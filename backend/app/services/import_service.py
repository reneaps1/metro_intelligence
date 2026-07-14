"""F4.5 (MI-25): file import pipeline orchestration.

Upload -> validate (connector-specific, hardened) -> dedup by sha256 ->
raw bytes retained in object storage -> parse -> normalize into the
canonical measurement model -> immutable insert. Invalid rows are
quarantined with a reason, never silently dropped (CLAUDE.md §6); the
`measurement_results` table itself is insert-only (DB trigger, migration
0003) so this module never updates or deletes a row once written -- a
corrected re-import would insert new rows, it does not exist yet as a
feature (out of F4.5's scope per docs/tasks/F4.5.md).

Each result's `deviation`/`is_ok` are computed by the compliance engine
(F7.D, `app.engines.compliance.evaluate`) against the specification version
active when the row was measured (CLAUDE.md §6) -- this pipeline calls the
engine, it does not reimplement the evaluation rule itself.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.base import FileValidationError, ParsedRow
from app.connectors.manual_upload import connector_for_filename
from app.core.config import get_settings
from app.engines.compliance.evaluate import SpecificationSnapshot
from app.engines.compliance.evaluate import evaluate as evaluate_compliance
from app.models.catalog import Characteristic, MeasurementProgram, PartNumber, Specification
from app.models.measurement import (
    DataSource,
    ImportedFile,
    MeasurementResult,
    MeasurementRun,
    MeasurementSample,
    QuarantinedRow,
)
from app.models.org import Machine
from app.services.audit_service import AuditContext, record_event
from app.services.storage_service import ObjectStorage

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
MANUAL_UPLOAD_DATA_SOURCE_CODE = "manual_upload"


@dataclass(frozen=True)
class ImportResult:
    imported_file: ImportedFile
    runs_created: int
    samples_created: int
    results_created: int
    quarantined_rows: list[QuarantinedRow]


class DuplicateImportError(Exception):
    def __init__(self, existing_file_id: uuid.UUID) -> None:
        self.existing_file_id = existing_file_id
        super().__init__(f"File already imported as {existing_file_id}.")


@dataclass
class _RunGroup:
    run: MeasurementRun
    used_sequences: set[int] = field(default_factory=set)

    def next_sequence(self, requested: int | None) -> int:
        if requested is not None and requested not in self.used_sequences:
            self.used_sequences.add(requested)
            return requested
        candidate = 1
        while candidate in self.used_sequences:
            candidate += 1
        self.used_sequences.add(candidate)
        return candidate


def _get_or_create_manual_upload_data_source(db: Session) -> DataSource:
    stmt = select(DataSource).where(DataSource.code == MANUAL_UPLOAD_DATA_SOURCE_CODE)
    data_source = db.execute(stmt).scalar_one_or_none()
    if data_source is not None:
        return data_source
    data_source = DataSource(
        code=MANUAL_UPLOAD_DATA_SOURCE_CODE,
        name="Manual file upload",
        source_type="manual_upload",
        description="Operator-initiated CSV/XLSX upload through the API.",
    )
    db.add(data_source)
    db.flush()
    return data_source


def _parse_datetime(raw: str) -> datetime | None:
    try:
        value = datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
    if value.tzinfo is None:
        return None
    return value


def _parse_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError, TypeError):
        return None


class _RowProcessor:
    def __init__(self, db: Session, imported_file_id: uuid.UUID) -> None:
        self.db = db
        self.imported_file_id = imported_file_id
        self._parts: dict[str, PartNumber | None] = {}
        self._programs: dict[uuid.UUID, MeasurementProgram | None] = {}
        self._characteristics: dict[tuple[uuid.UUID, str], Characteristic | None] = {}
        self._specifications: dict[uuid.UUID, Specification | None] = {}
        self._machines: dict[str, Machine | None] = {}
        self._run_groups: dict[tuple[uuid.UUID, datetime, str | None, str | None, str | None], _RunGroup] = {}
        self.runs_created = 0
        self.samples_created = 0
        self.results_created = 0
        self.quarantined: list[QuarantinedRow] = []

    def _quarantine(self, row: ParsedRow, reason: str) -> None:
        self.quarantined.append(
            QuarantinedRow(
                imported_file_id=self.imported_file_id,
                row_number=row.row_number,
                raw_row=row.data,
                reason=reason,
            )
        )

    def _part_for(self, code: str) -> PartNumber | None:
        if code not in self._parts:
            self._parts[code] = self.db.execute(
                select(PartNumber).where(PartNumber.code == code)
            ).scalar_one_or_none()
        return self._parts[code]

    def _active_program_for(self, part: PartNumber) -> MeasurementProgram | None:
        if part.id not in self._programs:
            self._programs[part.id] = (
                self.db.execute(
                    select(MeasurementProgram).where(
                        MeasurementProgram.part_number_id == part.id,
                        MeasurementProgram.valid_to.is_(None),
                    )
                )
                .scalars()
                .first()
            )
        return self._programs[part.id]

    def _characteristic_for(self, part_id: uuid.UUID, balloon: str) -> Characteristic | None:
        key = (part_id, balloon)
        if key not in self._characteristics:
            self._characteristics[key] = self.db.execute(
                select(Characteristic).where(
                    Characteristic.part_number_id == part_id,
                    Characteristic.balloon_number == balloon,
                )
            ).scalar_one_or_none()
        return self._characteristics[key]

    def _active_specification_for(self, characteristic_id: uuid.UUID) -> Specification | None:
        if characteristic_id not in self._specifications:
            self._specifications[characteristic_id] = self.db.execute(
                select(Specification).where(
                    Specification.characteristic_id == characteristic_id,
                    Specification.valid_to.is_(None),
                )
            ).scalar_one_or_none()
        return self._specifications[characteristic_id]

    def _machine_for(self, code: str) -> Machine | None:
        if not code:
            return None
        if code not in self._machines:
            self._machines[code] = (
                self.db.execute(select(Machine).where(Machine.code == code)).scalars().first()
            )
        return self._machines[code]

    def _run_group_for(
        self, part: PartNumber, program: MeasurementProgram, run_at: datetime, row: ParsedRow
    ) -> _RunGroup:
        key = (
            part.id,
            run_at,
            row.data.get("batch_lot") or None,
            row.data.get("machine_code") or None,
            row.data.get("operator_identifier") or None,
        )
        group = self._run_groups.get(key)
        if group is None:
            machine = self._machine_for(row.data.get("machine_code", ""))
            run = MeasurementRun(
                measurement_program_id=program.id,
                machine_id=machine.id if machine else None,
                imported_file_id=self.imported_file_id,
                operator_identifier=row.data.get("operator_identifier") or None,
                batch_lot=row.data.get("batch_lot") or None,
                run_at=run_at,
            )
            self.db.add(run)
            self.db.flush()
            self.runs_created += 1
            group = _RunGroup(run=run)
            self._run_groups[key] = group
        return group

    def process(self, row: ParsedRow) -> None:
        # Formula injection is rejected at the whole-file validate() stage
        # (app.connectors.manual_upload) before parse_rows() ever runs, so
        # by the time a row reaches here it has already cleared that check.
        part_code = row.data.get("part_number", "").strip()
        if not part_code:
            self._quarantine(row, "Missing part_number.")
            return
        part = self._part_for(part_code)
        if part is None:
            self._quarantine(row, f"Unknown part_number '{part_code}'.")
            return

        program = self._active_program_for(part)
        if program is None:
            self._quarantine(row, f"No active measurement program for part '{part_code}'.")
            return

        run_at_raw = row.data.get("run_at", "")
        run_at = _parse_datetime(run_at_raw)
        if run_at is None:
            self._quarantine(
                row, f"Invalid or missing run_at ('{run_at_raw}'); expected an ISO-8601 timestamp."
            )
            return

        sequence_raw = row.data.get("sample_sequence")
        requested_sequence: int | None = None
        if sequence_raw:
            try:
                requested_sequence = int(sequence_raw)
            except ValueError:
                requested_sequence = None

        group = self._run_group_for(part, program, run_at, row)
        sample = MeasurementSample(
            measurement_run_id=group.run.id,
            sample_sequence=group.next_sequence(requested_sequence),
            serial_number=row.data.get("serial_number") or None,
        )
        self.db.add(sample)
        self.db.flush()
        self.samples_created += 1

        for balloon, column in program.output_mapping.items():
            raw_value = row.data.get(column)
            if raw_value is None or raw_value == "":
                continue
            characteristic = self._characteristic_for(part.id, str(balloon))
            if characteristic is None:
                self._quarantine(
                    row, f"Unknown characteristic for balloon '{balloon}' on part '{part_code}'."
                )
                continue
            specification = self._active_specification_for(characteristic.id)
            if specification is None:
                self._quarantine(row, f"No active specification for characteristic balloon '{balloon}'.")
                continue
            value = _parse_decimal(raw_value)
            if value is None:
                self._quarantine(row, f"Non-numeric value '{raw_value}' in column '{column}'.")
                continue
            compliance = evaluate_compliance(
                value,
                SpecificationSnapshot(
                    nominal=specification.nominal,
                    lower_tol=specification.lower_tol,
                    upper_tol=specification.upper_tol,
                    unit=specification.unit,
                ),
            )
            self.db.add(
                MeasurementResult(
                    measured_at=run_at,
                    measurement_sample_id=sample.id,
                    characteristic_id=characteristic.id,
                    specification_id=specification.id,
                    value=value,
                    deviation=compliance.deviation,
                    is_ok=compliance.is_ok,
                )
            )
            self.results_created += 1


def process_upload(
    db: Session,
    storage: ObjectStorage,
    *,
    filename: str,
    content: bytes,
    declared_content_type: str | None,
    uploaded_by_user_id: uuid.UUID,
    audit_context: AuditContext,
) -> ImportResult:
    if len(content) > MAX_FILE_SIZE_BYTES:
        record_event(
            db,
            audit_context,
            action="upload_rejected",
            entity_type="measurement.imported_file",
            after={"filename": filename, "reason": "file exceeds maximum allowed size"},
        )
        db.commit()
        raise FileValidationError(
            f"File exceeds the maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    try:
        connector = connector_for_filename(filename)
        connector.validate(content, filename)
    except FileValidationError as exc:
        record_event(
            db,
            audit_context,
            action="upload_rejected",
            entity_type="measurement.imported_file",
            after={"filename": filename, "reason": str(exc)},
        )
        db.commit()
        raise

    sha256 = hashlib.sha256(content).hexdigest()
    existing = db.execute(select(ImportedFile).where(ImportedFile.sha256 == sha256)).scalar_one_or_none()
    if existing is not None:
        record_event(
            db,
            audit_context,
            action="upload_duplicate_detected",
            entity_type="measurement.imported_file",
            entity_id=existing.id,
            after={"filename": filename},
        )
        db.commit()
        raise DuplicateImportError(existing.id)

    settings = get_settings()
    data_source = _get_or_create_manual_upload_data_source(db)
    object_key = f"imports/{uuid.uuid4()}/{filename}"

    imported_file = ImportedFile(
        data_source_id=data_source.id,
        original_filename=filename,
        storage_bucket=settings.minio_bucket_raw_files,
        storage_object_key=object_key,
        sha256=sha256,
        size_bytes=len(content),
        content_type=declared_content_type,
        parse_status="parsing",
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(imported_file)
    db.flush()

    storage.put_object(
        settings.minio_bucket_raw_files,
        object_key,
        content,
        declared_content_type or "application/octet-stream",
    )

    rows = list(connector.parse_rows(content))
    if not rows:
        imported_file.parse_status = "error"
        imported_file.error_detail = "File has no data rows."
        record_event(
            db,
            audit_context,
            action="import_completed",
            entity_type="measurement.imported_file",
            entity_id=imported_file.id,
            after={"parse_status": imported_file.parse_status, "rows": 0},
        )
        db.commit()
        db.refresh(imported_file)
        return ImportResult(
            imported_file, runs_created=0, samples_created=0, results_created=0, quarantined_rows=[]
        )

    # Rows are processed against whichever measurement program their own
    # part_number resolves to, so a single upload can legitimately mix
    # parts -- every seeded program's output_mapping is the same shape,
    # {balloon_number: "COL_<balloon_number>"} (seed/generators/catalog.py).
    processor = _RowProcessor(db, imported_file.id)
    for row in rows:
        processor.process(row)

    db.add_all(processor.quarantined)

    if processor.results_created > 0:
        imported_file.parse_status = "parsed"
    elif processor.quarantined:
        imported_file.parse_status = "quarantined"
    else:
        imported_file.parse_status = "error"
        imported_file.error_detail = "No rows could be processed."

    record_event(
        db,
        audit_context,
        action="import_completed",
        entity_type="measurement.imported_file",
        entity_id=imported_file.id,
        after={
            "parse_status": imported_file.parse_status,
            "rows": len(rows),
            "runs_created": processor.runs_created,
            "samples_created": processor.samples_created,
            "results_created": processor.results_created,
            "quarantined_rows": len(processor.quarantined),
        },
    )
    db.commit()
    db.refresh(imported_file)
    return ImportResult(
        imported_file,
        runs_created=processor.runs_created,
        samples_created=processor.samples_created,
        results_created=processor.results_created,
        quarantined_rows=processor.quarantined,
    )
