"""Per-step process views (ADR-005): line overview, step detail,
characteristic detail and piece trace. Read-only; every endpoint requires
`process.operation.read`."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.security import User
from app.schemas.process import (
    CharacteristicDetail,
    LineOverview,
    LineRead,
    OperationSummary,
    PieceTrace,
    PositionMap,
)
from app.services import process_query_service as service

router = APIRouter(prefix="/process", tags=["process"])
READ = require_permission("process.operation", "read")


def _not_found(exc: service.NotFound) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/lines", response_model=list[LineRead])
def list_lines(db: Session = Depends(get_db), _user: User = Depends(READ)) -> list[LineRead]:
    return service.list_lines(db)


@router.get("/lines/{line_id}/overview", response_model=LineOverview)
def line_overview(
    line_id: uuid.UUID,
    start: date | None = Query(default=None, alias="from"),
    end: date | None = Query(default=None, alias="to"),
    recipe_id: list[uuid.UUID] = Query(default_factory=list),
    db: Session = Depends(get_db),
    _user: User = Depends(READ),
) -> LineOverview:
    try:
        return service.line_overview(db, line_id, start, end, recipe_id)
    except service.NotFound as exc:
        raise _not_found(exc) from exc


@router.get("/operations/{operation_id}/summary", response_model=OperationSummary)
def operation_summary(
    operation_id: uuid.UUID,
    start: date | None = Query(default=None, alias="from"),
    end: date | None = Query(default=None, alias="to"),
    recipe_id: list[uuid.UUID] = Query(default_factory=list),
    db: Session = Depends(get_db),
    _user: User = Depends(READ),
) -> OperationSummary:
    try:
        return service.operation_summary(db, operation_id, start, end, recipe_id)
    except service.NotFound as exc:
        raise _not_found(exc) from exc


@router.get(
    "/operations/{operation_id}/characteristics/{characteristic_id}", response_model=CharacteristicDetail
)
def characteristic_detail(
    operation_id: uuid.UUID,
    characteristic_id: uuid.UUID,
    start: date | None = Query(default=None, alias="from"),
    end: date | None = Query(default=None, alias="to"),
    recipe_id: list[uuid.UUID] = Query(default_factory=list),
    bins: int = Query(default=30, ge=5, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(READ),
) -> CharacteristicDetail:
    try:
        return service.characteristic_detail(db, operation_id, characteristic_id, start, end, recipe_id, bins)
    except service.NotFound as exc:
        raise _not_found(exc) from exc


@router.get("/operations/{operation_id}/position-map", response_model=PositionMap)
def position_map(
    operation_id: uuid.UUID,
    pin: int | None = Query(default=None, ge=1, le=99),
    start: date | None = Query(default=None, alias="from"),
    end: date | None = Query(default=None, alias="to"),
    recipe_id: list[uuid.UUID] = Query(default_factory=list),
    bins: int = Query(default=service.POSITION_BINS_DEFAULT, ge=10, le=80),
    db: Session = Depends(get_db),
    _user: User = Depends(READ),
) -> PositionMap:
    """X/Y position deviations of one pin against the drawing tolerance."""
    try:
        return service.position_map(db, operation_id, pin, start, end, recipe_id, bins)
    except service.NotFound as exc:
        raise _not_found(exc) from exc


@router.get("/pieces/{serial_number}", response_model=PieceTrace)
def piece_trace(
    serial_number: str,
    db: Session = Depends(get_db),
    _user: User = Depends(READ),
) -> PieceTrace:
    if not serial_number.isalnum() or len(serial_number) > 64:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid piece id.")
    try:
        return service.piece_trace(db, serial_number)
    except service.NotFound as exc:
        raise _not_found(exc) from exc
