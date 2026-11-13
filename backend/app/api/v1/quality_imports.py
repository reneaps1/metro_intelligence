"""IQ-F6: exploratory dimensional CSV import (industrial edition only).

Two steps, both on the head of the user's file:

1. ``POST /quality-analytics/imports/preview`` -- first rows, detected
   encoding / delimiter / decimal mark, inferred column types and a
   suggested mapping. Nothing is kept.
2. ``POST /quality-analytics/datasets`` -- applies the confirmed mapping,
   validates and quarantines rows, and keeps the resulting dataset in memory
   for its owner (decision D6, `services/imported_dataset_store.py`); the
   quality analytics endpoints then accept its id like the demo dataset.

Files above ``DIMENSIONAL_IMPORT_MAX_MB`` are not rejected: the browser sends
only their head and the response says which share of the file was analysed.
A full-file analysis belongs in an offline batch job, never a web request
(see `app/connectors/README.md`).

RBAC: ``measurement.imported_file:create`` (D4: reuse the import permission).

No ``from __future__ import annotations``: FastAPI's ``UploadFile`` form
detection needs real runtime types (same as ``app.api.v1.imports``).
"""

import hashlib
import json
import time
import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.v1.quality_analytics import dataset_out
from app.connectors.base import FileValidationError
from app.connectors.dimensional_csv import (
    ColumnMapping,
    MappingError,
    VariableSpec,
    build_dataset,
    decode,
    sniff,
    trim_partial_line,
)
from app.core.config import get_settings
from app.core.database import get_db
from app.core.edition import require_industrial_edition
from app.core.ratelimit import limiter
from app.core.security import require_permission
from app.models.security import User
from app.schemas.quality_imports import (
    ColumnMappingIn,
    ColumnProfileOut,
    ImportedDatasetResponse,
    ImportLimits,
    ImportReport,
    PreviewResponse,
    QuarantineExample,
    QuarantineReason,
    SampleNotice,
    SuggestedMappingOut,
)
from app.services.audit_service import AuditContext, get_audit_context, record_event
from app.services.imported_dataset_store import (
    IMPORTED_PREFIX,
    StoredDataset,
    get_imported_dataset_store,
    new_dataset_id,
)

router = APIRouter(
    prefix="/quality-analytics",
    tags=["quality-analytics"],
    dependencies=[Depends(require_industrial_edition)],
)

PREVIEW_MAX_BYTES = 256 * 1024
MAX_FILE_SIZE_DECLARED = 1024**4  # 1 TiB: only used for the sample notice
_create = require_permission("measurement.imported_file", "create")
_unprocessable = status.HTTP_422_UNPROCESSABLE_ENTITY


def _max_bytes() -> int:
    return get_settings().dimensional_import_max_mb * 1024 * 1024


def _check_upload(file: UploadFile, file_size: int) -> None:
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(_unprocessable, detail="Solo se aceptan archivos .csv o .txt.")
    if not 0 < file_size <= MAX_FILE_SIZE_DECLARED:
        raise HTTPException(_unprocessable, detail="Tamaño de archivo inválido.")


async def _read_head(file: UploadFile, cap: int, file_size: int) -> tuple[bytes, bool]:
    """Read at most ``cap`` bytes. Returns (content, is_head_of_larger_file)."""
    content = await file.read(cap + 1)
    truncated = len(content) > cap or file_size > len(content)
    content = content[:cap]
    return (trim_partial_line(content) if truncated else content), truncated


@router.post("/imports/preview", response_model=PreviewResponse)
@limiter.limit("30/minute")
async def preview_import(
    request: Request,
    file: UploadFile = File(...),
    file_size: int = Form(...),
    delimiter: str | None = Form(None, max_length=1),
    _user: User = Depends(_create),
) -> PreviewResponse:
    _check_upload(file, file_size)
    content, _ = await _read_head(file, PREVIEW_MAX_BYTES, file_size)
    try:
        result = sniff(content, delimiter or None)
    except FileValidationError as exc:
        raise HTTPException(_unprocessable, detail=str(exc)) from exc
    return PreviewResponse(
        encoding=result.encoding,
        delimiter=result.delimiter,
        decimal=result.decimal,  # type: ignore[arg-type]
        date_order=result.date_order,
        header=result.header,
        rows=result.rows,
        profiles=[ColumnProfileOut.model_validate(asdict(p)) for p in result.profiles],
        suggestion=SuggestedMappingOut.model_validate(asdict(result.suggestion)),
        sampled_rows=result.sampled_rows,
        limits=ImportLimits(max_bytes=_max_bytes(), max_rows=get_settings().dimensional_import_max_rows),
    )


def _mapping(raw: str) -> ColumnMappingIn:
    try:
        return ColumnMappingIn.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        message = "Mapeo inválido."
        if isinstance(exc, ValidationError) and exc.errors():
            message = f"Mapeo inválido: {exc.errors()[0]['msg']}"
        raise HTTPException(_unprocessable, detail=message) from None


@router.post("/datasets", response_model=ImportedDatasetResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_imported_dataset(
    request: Request,
    file: UploadFile = File(...),
    mapping: str = Form(..., max_length=32_000),
    file_size: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(_create),
    context: AuditContext = Depends(get_audit_context),
) -> ImportedDatasetResponse:
    _check_upload(file, file_size)
    m = _mapping(mapping)
    content, truncated = await _read_head(file, _max_bytes(), file_size)
    dataset_id = new_dataset_id()
    filename = file.filename[:120]  # type: ignore[index]
    try:
        text, _encoding = decode(content)
        dataset, report = build_dataset(
            text,
            delimiter=m.delimiter,
            decimal=m.decimal,
            mapping=ColumnMapping(
                layout=m.layout,
                timestamp=m.timestamp,
                time=m.time,
                date_order=m.date_order,
                piece_id=m.piece_id,
                group=m.group,
                cavity=m.cavity,
                machine=m.machine,
                shift=m.shift,
                batch=m.batch,
                ok_nok=m.ok_nok,
                variable=m.variable,
                value=m.value,
                nominal=m.nominal,
                lsl=m.lsl,
                usl=m.usl,
                unit=m.unit,
                value_columns=tuple(m.value_columns),
                specs={k: VariableSpec(**v.model_dump()) for k, v in m.specs.items()},
            ),
            max_rows=get_settings().dimensional_import_max_rows,
            dataset_id=dataset_id,
            # The origin ("Importado") is shown by the UI from source_type.
            name=m.name or filename,
            truncated=truncated,
            sent_fraction=len(content) / file_size,
        )
    except (FileValidationError, MappingError) as exc:
        raise HTTPException(_unprocessable, detail=str(exc)) from exc

    out = ImportReport(
        filename=filename,
        layout=report.layout,
        rows_read=report.rows_read,
        rows_accepted=report.rows_accepted,
        rows_quarantined=report.rows_quarantined,
        pieces=report.pieces,
        variables=report.variables,
        empty_values=report.empty_values,
        quarantine_by_reason=[
            QuarantineReason(reason=r, rows=n) for r, n in report.quarantine_counts.most_common()
        ],
        quarantine_examples=[
            QuarantineExample(row_number=r, reason=why) for r, why in report.quarantine_examples
        ],
        warnings=report.warnings,
        sample=SampleNotice(
            limited=report.sample_limited,
            rows_read=report.rows_read,
            approx_file_pct=None
            if report.approx_file_fraction is None
            else report.approx_file_fraction * 100,
            file_bytes=file_size,
            bytes_analysed=len(content),
        ),
    )
    audit_after: dict[str, Any] = {
        "filename": filename,
        "sha256_analysed_bytes": hashlib.sha256(content).hexdigest(),
        "layout": report.layout,
        "rows_read": report.rows_read,
        "rows_accepted": report.rows_accepted,
        "rows_quarantined": report.rows_quarantined,
        "sample_limited": report.sample_limited,
        "persisted": False,
    }
    record_event(
        db,
        context,
        action="dimensional_dataset_imported" if dataset else "dimensional_dataset_rejected",
        entity_type="quality_analytics.imported_dataset",
        entity_id=uuid.UUID(dataset_id.removeprefix(IMPORTED_PREFIX)),
        after=audit_after,
    )
    db.commit()
    if dataset is None:
        return ImportedDatasetResponse(report=out, dataset=None)
    get_imported_dataset_store().put(
        StoredDataset(dataset, user.id, time.time(), filename, out.model_dump(mode="json"))
    )
    return ImportedDatasetResponse(report=out, dataset=dataset_out(dataset))


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_imported_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(_create),
    context: AuditContext = Depends(get_audit_context),
) -> None:
    if not get_imported_dataset_store().delete(dataset_id, user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    record_event(
        db,
        context,
        action="dimensional_dataset_discarded",
        entity_type="quality_analytics.imported_dataset",
        entity_id=uuid.UUID(dataset_id.removeprefix(IMPORTED_PREFIX)),
    )
    db.commit()
