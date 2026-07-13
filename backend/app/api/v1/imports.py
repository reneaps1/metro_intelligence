"""F4.5 (MI-25): /imports router -- upload (metrologist+) and status lookup.

Upload handling reads the whole file into memory up front (demo-scale CSV/
XLSX files, capped at ``import_service.MAX_FILE_SIZE_BYTES``) rather than
streaming, since every validation step (magic bytes, zip-bomb guard, sha256)
needs the complete content anyway.

No ``from __future__ import annotations`` here (unlike most of this
codebase): FastAPI's ``UploadFile`` form-parameter detection needs the real
runtime type, not a postponed-evaluation string -- same reason
``app.api.v1.auth`` omits it.
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.base import FileValidationError
from app.core.database import get_db
from app.core.ratelimit import limiter
from app.core.security import require_permission
from app.models.measurement import (
    ImportedFile,
    MeasurementResult,
    MeasurementRun,
    MeasurementSample,
    QuarantinedRow,
)
from app.models.security import User
from app.schemas.imports import ImportedFileRead, QuarantinedRowRead
from app.services.audit_service import AuditContext, get_audit_context
from app.services.import_service import DuplicateImportError, ImportResult, process_upload
from app.services.storage_service import ObjectStorage, get_object_storage

router = APIRouter(prefix="/imports", tags=["imports"])


def _counts_for(db: Session, imported_file_id: uuid.UUID) -> tuple[int, int, int]:
    runs = db.execute(
        select(func.count())
        .select_from(MeasurementRun)
        .where(MeasurementRun.imported_file_id == imported_file_id)
    ).scalar_one()
    samples = db.execute(
        select(func.count())
        .select_from(MeasurementSample)
        .join(MeasurementRun, MeasurementSample.measurement_run_id == MeasurementRun.id)
        .where(MeasurementRun.imported_file_id == imported_file_id)
    ).scalar_one()
    results = db.execute(
        select(func.count())
        .select_from(MeasurementResult)
        .join(MeasurementSample, MeasurementResult.measurement_sample_id == MeasurementSample.id)
        .join(MeasurementRun, MeasurementSample.measurement_run_id == MeasurementRun.id)
        .where(MeasurementRun.imported_file_id == imported_file_id)
    ).scalar_one()
    return runs, samples, results


def _read_model_from_result(result: ImportResult) -> ImportedFileRead:
    return ImportedFileRead(
        id=result.imported_file.id,
        original_filename=result.imported_file.original_filename,
        sha256=result.imported_file.sha256,
        size_bytes=result.imported_file.size_bytes,
        content_type=result.imported_file.content_type,
        parse_status=result.imported_file.parse_status,
        error_detail=result.imported_file.error_detail,
        created_at=result.imported_file.created_at,
        runs_created=result.runs_created,
        samples_created=result.samples_created,
        results_created=result.results_created,
        quarantined_rows=[QuarantinedRowRead.model_validate(row) for row in result.quarantined_rows],
    )


def _read_model_from_db(db: Session, imported_file: ImportedFile) -> ImportedFileRead:
    runs, samples, results = _counts_for(db, imported_file.id)
    quarantined = (
        db.execute(
            select(QuarantinedRow)
            .where(QuarantinedRow.imported_file_id == imported_file.id)
            .order_by(QuarantinedRow.row_number)
        )
        .scalars()
        .all()
    )
    return ImportedFileRead(
        id=imported_file.id,
        original_filename=imported_file.original_filename,
        sha256=imported_file.sha256,
        size_bytes=imported_file.size_bytes,
        content_type=imported_file.content_type,
        parse_status=imported_file.parse_status,
        error_detail=imported_file.error_detail,
        created_at=imported_file.created_at,
        runs_created=runs,
        samples_created=samples,
        results_created=results,
        quarantined_rows=[QuarantinedRowRead.model_validate(row) for row in quarantined],
    )


@router.post("", response_model=ImportedFileRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_import(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("measurement.imported_file", "create")),
    context: AuditContext = Depends(get_audit_context),
    storage: ObjectStorage = Depends(get_object_storage),
) -> ImportedFileRead:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No filename provided.")
    content = await file.read()
    try:
        result = process_upload(
            db,
            storage,
            filename=file.filename,
            content=content,
            declared_content_type=file.content_type,
            uploaded_by_user_id=current_user.id,
            audit_context=context,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except DuplicateImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "This file has already been imported.",
                "imported_file_id": str(exc.existing_file_id),
            },
        ) from exc
    return _read_model_from_result(result)


@router.get("/{imported_file_id}", response_model=ImportedFileRead)
def get_import(
    imported_file_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("measurement.imported_file", "read")),
) -> ImportedFileRead:
    imported_file = db.get(ImportedFile, imported_file_id)
    if imported_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imported file not found.")
    return _read_model_from_db(db, imported_file)
