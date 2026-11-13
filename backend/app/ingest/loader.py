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
from contextlib import ExitStack
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
from app.models import ImportedFile, Specification
from app.models.base import uuid7
from app.services.storage_service import ObjectStorage

logger = logging.getLogger(__name__)

AUDIT_ACTION = "line_file_ingested"
AUDIT_ACTOR = "cli:ingest_line"
NOT_RETAINED_BUCKET = "not-retained"
# Pieces per COPY flush inside a file's transaction (bounds memory).
COPY_CHUNK_ROWS = 2000
STEP_RESULTS_COPY = (
    "process_step_results (id, part_instance_id, operation_id, measurement_sample_id, "
    "recorded_at, nest, program_number, machine_ok, error_count, reference_ok, attempt_no)"
)


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


class RecipeIndex:
    """Piece id -> recipe in little memory (the API host may have 512 MB).

    Numeric ids (the stations' sequential counters) live in a bytearray
    indexed by the id, one byte each; anything else falls back to a dict.
    Byte 0 = unknown piece, 255 = known piece without a recipe number.
    """

    _MAX_NUMERIC = 100_000_000
    _NO_RECIPE = 255

    def __init__(self) -> None:
        self._codes = bytearray()
        self._other: dict[str, int | None] = {}
        self.count = 0

    def _numeric(self, serial: str) -> int | None:
        if serial.isdigit() and not (len(serial) > 1 and serial[0] == "0"):
            value = int(serial)
            if value < self._MAX_NUMERIC:
                return value
        return None

    def set(self, serial: str, recipe: int | None) -> None:
        index = self._numeric(serial)
        if index is None or (recipe is not None and not 0 <= recipe < self._NO_RECIPE - 1):
            if serial not in self._other:
                self.count += 1
            self._other[serial] = recipe
            return
        if index >= len(self._codes):
            self._codes.extend(bytes(max(index + 1 - len(self._codes), len(self._codes) // 2)))
        if self._codes[index] == 0:
            self.count += 1
        self._codes[index] = self._NO_RECIPE if recipe is None else recipe + 1

    def lookup(self, serial: str) -> tuple[bool, int | None]:
        """(known, recipe)."""
        index = self._numeric(serial)
        if index is None or serial in self._other:
            return serial in self._other, self._other.get(serial)
        code = self._codes[index] if index < len(self._codes) else 0
        if code == 0:
            return False, None
        return True, None if code == self._NO_RECIPE else code - 1


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
        self.recipes = RecipeIndex()
        self.loaded_hashes: set[str] = set()
        self.specs: dict[uuid.UUID, list[SpecVersion]] = {}

    # ------------------------------------------------------------------ state
    def scan_recipes(self) -> int:
        """Map piece id -> recipe from every type-check file (fast pass)."""
        station = self.config.type_check
        for path in station_files(self.data_dir, station):
            for serial, program in read_type_check_programs(path):
                self.recipes.set(serial, program)
        return self.recipes.count

    def load_state(self) -> None:
        """Resume: files already loaded and the specification versions.
        Pieces and attempts are looked up per file, so memory stays flat."""
        with Session(self.engine) as session:
            self.loaded_hashes = set(
                session.execute(
                    select(ImportedFile.sha256).where(
                        ImportedFile.data_source_id == self.catalog.data_source_id,
                        ImportedFile.parse_status == "parsed",
                    )
                ).scalars()
            )
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
        known, recipe = self.recipes.lookup(row.serial)
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
        return self.recipes.lookup(serial)[1] in self.config.recipes_in_scope

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
        recipe_ids = self.catalog.recipes

        file_id = uuid7()
        run_id = uuid7()
        quarantined: list[tuple[Any, ...]] = []
        kept: list[tuple[StationRow, int | None]] = []
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
            if keep:
                kept.append((item, recipe))

        instances, attempts = self._existing(operation_id, {row.serial for row, _ in kept})

        storage_key = ""
        bucket = NOT_RETAINED_BUCKET
        if self.storage is not None and not dry_run:
            storage_key = f"line-ingest/{self.config.line.code}/{station.code}/{sha256}.csv"
            self.storage.put_object(self.raw_bucket, storage_key, data, "text/csv")
            bucket = self.raw_bucket

        # One transaction per file, opened before the rows are built: rows go
        # to COPY in chunks so memory stays flat however large the file is.
        with ExitStack() as stack:
            conn: psycopg.Connection[Any] | None = None
            if not dry_run:
                conn = stack.enter_context(psycopg.connect(_psycopg_url(self.engine)))
                stack.enter_context(conn.transaction())
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
                if kept:
                    conn.execute(
                        "INSERT INTO measurement_runs "
                        "(id, measurement_program_id, machine_id, imported_file_id, run_at) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (
                            run_id,
                            ids.program_id,
                            ids.machine_id,
                            file_id,
                            min(r.recorded_at for r, _ in kept),
                        ),
                    )

            new_instances: list[tuple[Any, ...]] = []
            samples: list[tuple[Any, ...]] = []
            steps: list[tuple[Any, ...]] = []
            results: list[tuple[Any, ...]] = []

            def flush() -> None:
                if conn is not None:
                    _copy(
                        conn,
                        "process_part_instances (id, line_id, serial_number, recipe_id, first_seen_at)",
                        new_instances,
                    )
                    _copy(
                        conn,
                        "measurement_samples (id, measurement_run_id, sample_sequence, serial_number)",
                        samples,
                    )
                    _copy(
                        conn,
                        STEP_RESULTS_COPY,
                        steps,
                    )
                    _copy(
                        conn,
                        "measurement_results (id, measured_at, measurement_sample_id, characteristic_id, "
                        "specification_id, value, deviation, is_ok, machine_ok, machine_code)",
                        results,
                    )
                for rows in (new_instances, samples, steps, results):
                    rows.clear()

            for sequence, (item, recipe) in enumerate(kept, start=1):
                serial = item.serial
                instance_id = instances.get(serial)
                if instance_id is None:
                    instance_id = uuid7()
                    instances[serial] = instance_id
                    recipe_id = recipe_ids.get(recipe) if recipe is not None else None
                    if recipe_id is None:
                        outcome.pieces_without_recipe += 1
                    new_instances.append(
                        (instance_id, self.catalog.line_id, serial, recipe_id, item.recorded_at)
                    )

                attempt = attempts.get(serial, 0) + 1
                attempts[serial] = attempt
                if attempt > 1:
                    outcome.repeat_attempts += 1

                sample_id = uuid7()
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
                if len(samples) >= COPY_CHUNK_ROWS:
                    flush()
            flush()

            if conn is None:
                return outcome
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

        self.loaded_hashes.add(sha256)
        return outcome

    def _existing(
        self, operation_id: uuid.UUID, serials: set[str]
    ) -> tuple[dict[str, uuid.UUID], dict[str, int]]:
        """Pieces already stored among `serials`, and their highest attempt
        at this operation (both indexed lookups)."""
        if not serials:
            return {}, {}
        with psycopg.connect(_psycopg_url(self.engine)) as conn:
            instances: dict[str, uuid.UUID] = dict(
                conn.execute(
                    "SELECT serial_number, id FROM process_part_instances "
                    "WHERE line_id = %s AND serial_number = ANY(%s)",
                    (self.catalog.line_id, list(serials)),
                ).fetchall()
            )
            attempts: dict[str, int] = (
                dict(
                    conn.execute(
                        "SELECT pi.serial_number, max(sr.attempt_no) FROM process_step_results sr "
                        "JOIN process_part_instances pi ON pi.id = sr.part_instance_id "
                        "WHERE sr.operation_id = %s AND pi.id = ANY(%s) GROUP BY pi.serial_number",
                        (operation_id, list(instances.values())),
                    ).fetchall()
                )
                if instances
                else {}
            )
        return instances, attempts


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
