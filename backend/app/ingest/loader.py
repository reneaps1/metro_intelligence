"""Load station files into the process model with PostgreSQL COPY.

Order and scope (ADR-005):
1. A fast pass over the type-check files maps every piece id to its recipe.
2. The type-check station loads first: pieces of an in-scope recipe become
   part instances with that recipe. Other recipes are counted and skipped.
3. Every other station keeps a row only if the piece belongs to the scope:
   - stations with a program column: program in the station's list and the
     piece's recipe, when known, in scope. Pieces never seen at type check
     (scrapped before it) are kept as instances without recipe.
   - stations without a program column: the piece's recipe must be known and
     in scope; otherwise the row is counted as "scope unknown" and skipped.

Each file is one transaction (raw file to object storage, imported file,
run, samples, step results, results, quarantined rows, one audit entry), so
an interrupted load resumes at the first file not yet marked parsed.
Out-of-scope rows are never written anywhere.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.engines.compliance.evaluate import SpecificationSnapshot, evaluate
from app.ingest.config import IngestConfig, StationConfig
from app.ingest.setup import LineCatalog, ensure_characteristic
from app.ingest.stations import BadRow, StationRow, read_station_file, read_type_check_programs, station_files
from app.models import ImportedFile, PartInstance, Specification, StepResult
from app.models.base import uuid7
from app.services.storage_service import ObjectStorage

logger = logging.getLogger(__name__)

AUDIT_ACTION = "line_file_ingested"
AUDIT_ACTOR = "cli:ingest_line"
NOT_RETAINED_BUCKET = "not-retained"


@dataclass(frozen=True)
class SpecVersion:
    specification_id: uuid.UUID
    valid_from: datetime
    valid_to: datetime | None
    snapshot: SpecificationSnapshot


@dataclass
class FileOutcome:
    """Row accounting for one file: read = loaded + excluded + skipped + quarantined."""

    station: str
    file: str
    rows_read: int = 0
    rows_loaded: int = 0
    values_loaded: int = 0
    excluded_recipe: int = 0
    excluded_program: int = 0
    scope_unknown: int = 0
    quarantined: int = 0
    repeat_attempts: int = 0
    pieces_without_recipe: int = 0
    skipped_already_loaded: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k not in ("station", "file")}


@dataclass
class LoadSummary:
    files: list[FileOutcome] = field(default_factory=list)

    def totals_by_station(self) -> dict[str, Counter[str]]:
        totals: dict[str, Counter[str]] = {}
        for outcome in self.files:
            counter = totals.setdefault(outcome.station, Counter())
            counter["files"] += 1
            counter["files_skipped"] += int(outcome.skipped_already_loaded)
            for key, value in outcome.as_dict().items():
                if isinstance(value, int) and not isinstance(value, bool):
                    counter[key] += value
        return totals


def _psycopg_url(engine: Engine) -> str:
    return engine.url.set(drivername="postgresql").render_as_string(hide_password=False)


class LineLoader:
    def __init__(
        self,
        engine: Engine,
        config: IngestConfig,
        catalog: LineCatalog,
        data_dir: Path,
        storage: ObjectStorage | None,
        raw_bucket: str,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.engine = engine
        self.config = config
        self.catalog = catalog
        self.data_dir = data_dir
        self.storage = storage
        self.raw_bucket = raw_bucket
        self.progress = progress or (lambda message: logger.info(message))
        self.recipe_by_serial: dict[str, int | None] = {}
        self.instance_by_serial: dict[str, uuid.UUID] = {}
        self.seen_by_operation: dict[uuid.UUID, set[str]] = {}
        self.extra_attempts: dict[tuple[str, uuid.UUID], int] = {}
        self.loaded_hashes: set[str] = set()
        self.specs: dict[uuid.UUID, list[SpecVersion]] = {}

    # ------------------------------------------------------------------ state
    def scan_recipes(self) -> int:
        """Map piece id -> recipe from every type-check file (fast pass)."""
        station = self.config.type_check
        for path in station_files(self.data_dir, station):
            for serial, program in read_type_check_programs(path):
                self.recipe_by_serial[serial] = program
        return len(self.recipe_by_serial)

    def load_state(self) -> None:
        """Resume: already-loaded files, existing pieces and attempts, specs."""
        with Session(self.engine) as session:
            self.loaded_hashes = set(
                session.execute(
                    select(ImportedFile.sha256).where(
                        ImportedFile.data_source_id == self.catalog.data_source_id,
                        ImportedFile.parse_status == "parsed",
                    )
                ).scalars()
            )
            for serial, instance_id in session.execute(
                select(PartInstance.serial_number, PartInstance.id).where(
                    PartInstance.line_id == self.catalog.line_id
                )
            ):
                self.instance_by_serial[serial] = instance_id
            serial_by_instance = {v: k for k, v in self.instance_by_serial.items()}
            for instance_id, operation_id, attempts in session.execute(
                select(StepResult.part_instance_id, StepResult.operation_id, StepResult.attempt_no).where(
                    StepResult.operation_id.in_([s.operation_id for s in self.catalog.stations.values()])
                )
            ):
                serial = serial_by_instance[instance_id]
                self.seen_by_operation.setdefault(operation_id, set()).add(serial)
                if attempts > 1:
                    key = (serial, operation_id)
                    self.extra_attempts[key] = max(self.extra_attempts.get(key, 0), attempts - 1)
            self.specs = load_spec_versions(session, list(self.catalog.characteristics.values()))

    def _spec_for(self, characteristic_id: uuid.UUID, measured_at: datetime) -> SpecVersion | None:
        for version in self.specs.get(characteristic_id, ()):
            if version.valid_from <= measured_at and (
                version.valid_to is None or measured_at < version.valid_to
            ):
                return version
        return None

    # ------------------------------------------------------------------ scope
    def _scope(
        self, station: StationConfig, row: StationRow, outcome: FileOutcome
    ) -> tuple[bool, int | None]:
        """(keep, recipe) for a parsed row; counts the reason when skipped."""
        in_scope = self.config.recipes_in_scope
        if station.kind == "type_check":
            if row.program in in_scope:
                return True, row.program
            outcome.excluded_recipe += 1
            return False, None
        if station.programs is not None and row.program not in station.programs:
            outcome.excluded_program += 1
            return False, None
        known = row.serial in self.recipe_by_serial
        recipe = self.recipe_by_serial.get(row.serial)
        if known and recipe not in in_scope:
            outcome.excluded_recipe += 1
            return False, None
        if not known and station.programs is None:
            outcome.scope_unknown += 1
            return False, None
        return True, recipe

    def _bad_row_in_scope(self, station: StationConfig, bad: BadRow) -> bool:
        program_text = bad.raw.get("Programmnummer", "").strip()
        program = int(program_text) if program_text.lstrip("+-").isdigit() else None
        if station.kind == "type_check":
            return program in self.config.recipes_in_scope
        if station.programs is not None:
            return program in station.programs
        values = list(bad.raw.values())  # the piece id is the second column
        serial = values[1].strip() if len(values) > 1 else ""
        return self.recipe_by_serial.get(serial) in self.config.recipes_in_scope

    # ------------------------------------------------------------------ files
    def load(
        self,
        station_codes: Iterable[str] | None = None,
        limit_files: int | None = None,
        dry_run: bool = False,
    ) -> LoadSummary:
        summary = LoadSummary()
        wanted = set(station_codes) if station_codes else None
        ordered = sorted(self.config.stations, key=lambda s: (s.kind != "type_check", s.sequence))
        for station in ordered:
            if wanted is not None and station.code not in wanted:
                continue
            files = station_files(self.data_dir, station)[:limit_files]
            started = time.monotonic()
            for index, path in enumerate(files, start=1):
                outcome = self.load_file(station, path, dry_run=dry_run)
                summary.files.append(outcome)
                if index % 20 == 0 or index == len(files):
                    elapsed = time.monotonic() - started
                    self.progress(
                        f"{station.code}: {index}/{len(files)} files, {elapsed:,.0f}s elapsed, "
                        f"ETA {elapsed / index * (len(files) - index):,.0f}s"
                    )
        return summary

    def load_file(self, station: StationConfig, path: Path, dry_run: bool = False) -> FileOutcome:
        relative = f"{station.folder}/{path.name}"
        outcome = FileOutcome(station=station.code, file=relative)
        data = path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        if sha256 in self.loaded_hashes:
            outcome.skipped_already_loaded = True
            return outcome

        ids = self.catalog.stations[station.code]
        operation_id = ids.operation_id
        seen = self.seen_by_operation.setdefault(operation_id, set())
        recipe_ids = self.catalog.recipes

        new_instances: list[tuple[Any, ...]] = []
        samples: list[tuple[Any, ...]] = []
        steps: list[tuple[Any, ...]] = []
        results: list[tuple[Any, ...]] = []
        quarantined: list[tuple[Any, ...]] = []
        pending_instances: dict[str, uuid.UUID] = {}
        pending_seen: set[str] = set()
        pending_attempts: dict[tuple[str, uuid.UUID], int] = {}
        file_id = uuid7()
        run_id = uuid7()
        run_at: datetime | None = None
        sequence = 0

        for item in read_station_file(path, station, self.config.pins, self.config.timezone):
            outcome.rows_read += 1
            if isinstance(item, BadRow):
                if self._bad_row_in_scope(station, item):
                    outcome.quarantined += 1
                    quarantined.append((uuid7(), file_id, item.row_number, json.dumps(item.raw), item.reason))
                elif station.programs is None and station.kind != "type_check":
                    outcome.scope_unknown += 1
                else:
                    outcome.excluded_program += 1
                continue

            keep, recipe = self._scope(station, item, outcome)
            if not keep:
                continue
            serial = item.serial
            instance_id = self.instance_by_serial.get(serial) or pending_instances.get(serial)
            if instance_id is None:
                instance_id = uuid7()
                pending_instances[serial] = instance_id
                recipe_id = recipe_ids.get(recipe) if recipe is not None else None
                if recipe_id is None:
                    outcome.pieces_without_recipe += 1
                new_instances.append((instance_id, self.catalog.line_id, serial, recipe_id, item.recorded_at))

            if serial in seen or serial in pending_seen:
                key = (serial, operation_id)
                extra = pending_attempts.get(key, self.extra_attempts.get(key, 0)) + 1
                pending_attempts[key] = extra
                attempt = extra + 1
                outcome.repeat_attempts += 1
            else:
                pending_seen.add(serial)
                attempt = 1

            sequence += 1
            sample_id = uuid7()
            run_at = item.recorded_at if run_at is None else min(run_at, item.recorded_at)
            samples.append((sample_id, run_id, sequence, serial))
            steps.append(
                (
                    uuid7(),
                    instance_id,
                    operation_id,
                    sample_id,
                    item.recorded_at,
                    item.nest,
                    item.program,
                    item.machine_ok,
                    item.error_count,
                    item.reference_ok,
                    attempt,
                )
            )
            for value in item.values:
                characteristic_id = self.catalog.characteristics.get((station.code, value.measure))
                if characteristic_id is None and dry_run:
                    # No writes in a dry run: track the new measure in memory only.
                    characteristic_id = uuid.uuid4()
                    self.catalog.characteristics[(station.code, value.measure)] = characteristic_id
                elif characteristic_id is None:
                    with Session(self.engine) as session:
                        characteristic_id = ensure_characteristic(
                            session, self.catalog, station, value.measure
                        )
                        session.commit()
                spec = self._spec_for(characteristic_id, item.recorded_at)
                deviation: Decimal | None = None
                is_ok: bool | None = None
                if spec is not None:
                    verdict = evaluate(value.value, spec.snapshot)
                    deviation, is_ok = verdict.deviation, verdict.is_ok
                results.append(
                    (
                        uuid7(),
                        item.recorded_at,
                        sample_id,
                        characteristic_id,
                        spec.specification_id if spec else None,
                        value.value,
                        deviation,
                        is_ok,
                        value.machine_ok,
                        value.machine_code,
                    )
                )
            outcome.rows_loaded += 1
            outcome.values_loaded += len(item.values)

        if dry_run:
            return outcome

        storage_key = ""
        bucket = NOT_RETAINED_BUCKET
        if self.storage is not None:
            storage_key = f"line-ingest/{self.config.line.code}/{station.code}/{sha256}.csv"
            self.storage.put_object(self.raw_bucket, storage_key, data, "text/csv")
            bucket = self.raw_bucket

        with psycopg.connect(_psycopg_url(self.engine)) as conn, conn.transaction():
            conn.execute(
                "INSERT INTO measurement_imported_files (id, data_source_id, connector_id, "
                "original_filename, storage_bucket, storage_object_key, sha256, size_bytes, "
                "content_type, parse_status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'text/csv', 'parsed')",
                (
                    file_id,
                    self.catalog.data_source_id,
                    self.catalog.connector_id,
                    relative,
                    bucket,
                    storage_key,
                    sha256,
                    len(data),
                ),
            )
            if steps:
                conn.execute(
                    "INSERT INTO measurement_runs "
                    "(id, measurement_program_id, machine_id, imported_file_id, run_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (run_id, ids.program_id, ids.machine_id, file_id, run_at),
                )
            _copy(
                conn,
                "process_part_instances (id, line_id, serial_number, recipe_id, first_seen_at)",
                new_instances,
            )
            _copy(
                conn, "measurement_samples (id, measurement_run_id, sample_sequence, serial_number)", samples
            )
            _copy(
                conn,
                "process_step_results (id, part_instance_id, operation_id, measurement_sample_id, "
                "recorded_at, nest, program_number, machine_ok, error_count, reference_ok, attempt_no)",
                steps,
            )
            _copy(
                conn,
                "measurement_results (id, measured_at, measurement_sample_id, characteristic_id, "
                "specification_id, value, deviation, is_ok, machine_ok, machine_code)",
                results,
            )
            _copy(
                conn,
                "measurement_quarantined_rows (id, imported_file_id, row_number, raw_row, reason)",
                quarantined,
            )
            conn.execute(
                "INSERT INTO security_audit_log "
                "(id, actor_identifier, action, entity_type, entity_id, after_state) "
                "VALUES (%s, %s, %s, 'imported_file', %s, %s)",
                (
                    uuid7(),
                    AUDIT_ACTOR,
                    AUDIT_ACTION,
                    file_id,
                    json.dumps({"station": station.code, "file": relative, **outcome.as_dict()}),
                ),
            )

        # Committed: promote this file's state.
        self.loaded_hashes.add(sha256)
        self.instance_by_serial.update(pending_instances)
        seen.update(pending_seen)
        self.extra_attempts.update(pending_attempts)
        return outcome


def _copy(conn: psycopg.Connection[Any], target: str, rows: list[tuple[Any, ...]]) -> None:
    if not rows:
        return
    with conn.cursor().copy(f"COPY {target} FROM STDIN") as copy:
        for row in rows:
            copy.write_row(row)


def load_spec_versions(
    session: Session, characteristic_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[SpecVersion]]:
    versions: dict[uuid.UUID, list[SpecVersion]] = {}
    for spec in session.execute(
        select(Specification).where(Specification.characteristic_id.in_(characteristic_ids))
    ).scalars():
        versions.setdefault(spec.characteristic_id, []).append(
            SpecVersion(
                specification_id=spec.id,
                valid_from=spec.valid_from,
                valid_to=spec.valid_to,
                snapshot=SpecificationSnapshot(
                    nominal=spec.nominal, lower_tol=spec.lower_tol, upper_tol=spec.upper_tol, unit=spec.unit
                ),
            )
        )
    return versions
