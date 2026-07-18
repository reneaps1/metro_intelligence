"""F4.6 (MI-26): read-only measurements API -- runs, run detail, and the
characteristic time series that feeds trend/SPC charts.

Read-only end to end: measurements enter via F4.5's import pipeline and are
immutable once written (DB trigger, migration 0003) -- nothing here ever
inserts/updates/deletes a MeasurementResult/Sample/Run.

RBAC note: docs/tasks/F4.6.md's own acceptance criteria says "viewer puede
leer", but docs/security/rbac.md's actual matrix (and migration 0001's
ROLE_PERMISSIONS, the source of truth) does *not* grant `viewer` read on
`measurement.measurement_run`/`measurement_result` -- only metrologist,
quality_engineer, admin, auditor. Followed the matrix, not the task file's
inconsistent prose; flagged explicitly in this PR's description. A viewer's
path to quality data is the dashboard APIs (F6.2/F6.3), not raw series.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
from app.models.catalog import Characteristic, MeasurementProgram, Specification
from app.models.measurement import MeasurementResult, MeasurementRun, MeasurementSample
from app.models.security import User
from app.schemas.measurements import (
    CapabilityHistoryResponse,
    CapabilityWindowRead,
    ExperimentalDriftRead,
    MeasurementResultRead,
    MeasurementRunDetailRead,
    MeasurementRunRead,
    MeasurementSampleRead,
    Page,
    SamplingRecommendation,
    SeriesPoint,
    SeriesResponse,
    SpecificationSnapshot,
)
from app.services.adaptive_sampling_service import compute_adaptive_sampling_recommendation
from app.services.capability_history_service import compute_capability_history
from app.services.drift_detection_service import compute_experimental_drift

router = APIRouter(tags=["measurements"])

DEFAULT_MAX_POINTS = 500
HARD_MAX_POINTS = 5000


def _specification_snapshot(spec: Specification) -> SpecificationSnapshot:
    return SpecificationSnapshot.model_validate(spec)


def _compute_deviation_and_ok(value: Decimal, spec: Specification) -> tuple[Decimal, bool]:
    deviation = value - spec.nominal
    lower_ok = spec.lower_tol is None or deviation >= spec.lower_tol
    upper_ok = spec.upper_tol is None or deviation <= spec.upper_tol
    return deviation, (lower_ok and upper_ok)


def _result_read(result: MeasurementResult, spec: Specification) -> MeasurementResultRead:
    deviation, is_ok = _compute_deviation_and_ok(result.value, spec)
    return MeasurementResultRead(
        id=result.id,
        characteristic_id=result.characteristic_id,
        measured_at=result.measured_at,
        value=result.value,
        deviation=deviation,
        is_ok=is_ok,
        specification=_specification_snapshot(spec),
    )


def _part_number_id_for_run(run: MeasurementRun) -> uuid.UUID:
    return run.measurement_program.part_number_id


def _run_read(run: MeasurementRun) -> MeasurementRunRead:
    return MeasurementRunRead(
        id=run.id,
        measurement_program_id=run.measurement_program_id,
        part_number_id=_part_number_id_for_run(run),
        machine_id=run.machine_id,
        imported_file_id=run.imported_file_id,
        operator_identifier=run.operator_identifier,
        batch_lot=run.batch_lot,
        run_at=run.run_at,
        sample_count=len(run.samples),
    )


@router.get("/measurement-runs", response_model=Page[MeasurementRunRead])
def list_measurement_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    part_number_id: uuid.UUID | None = None,
    machine_id: uuid.UUID | None = None,
    measurement_program_id: uuid.UUID | None = None,
    run_at_from: datetime | None = None,
    run_at_to: datetime | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("measurement.measurement_run", "read")),
) -> Page[MeasurementRunRead]:
    filtered = select(MeasurementRun)
    if part_number_id is not None:
        filtered = filtered.join(
            MeasurementProgram, MeasurementRun.measurement_program_id == MeasurementProgram.id
        ).where(MeasurementProgram.part_number_id == part_number_id)
    if machine_id is not None:
        filtered = filtered.where(MeasurementRun.machine_id == machine_id)
    if measurement_program_id is not None:
        filtered = filtered.where(MeasurementRun.measurement_program_id == measurement_program_id)
    if run_at_from is not None:
        filtered = filtered.where(MeasurementRun.run_at >= run_at_from)
    if run_at_to is not None:
        filtered = filtered.where(MeasurementRun.run_at <= run_at_to)

    total = db.execute(select(func.count()).select_from(filtered.subquery())).scalar_one()

    page_stmt = (
        filtered.options(
            selectinload(MeasurementRun.samples), selectinload(MeasurementRun.measurement_program)
        )
        .order_by(MeasurementRun.run_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    rows = db.execute(page_stmt).scalars().all()
    return Page(items=[_run_read(run) for run in rows], total=total, page=page, page_size=page_size)


@router.get("/measurement-runs/{run_id}", response_model=MeasurementRunDetailRead)
def get_measurement_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("measurement.measurement_run", "read")),
) -> MeasurementRunDetailRead:
    stmt = (
        select(MeasurementRun)
        .where(MeasurementRun.id == run_id)
        .options(
            selectinload(MeasurementRun.measurement_program),
            selectinload(MeasurementRun.samples).selectinload(MeasurementSample.results),
        )
    )
    run = db.execute(stmt).unique().scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Measurement run not found.")

    spec_ids = {result.specification_id for sample in run.samples for result in sample.results}
    specs = {
        spec.id: spec
        for spec in db.execute(select(Specification).where(Specification.id.in_(spec_ids))).scalars().all()
    }

    samples_read = [
        MeasurementSampleRead(
            id=sample.id,
            sample_sequence=sample.sample_sequence,
            serial_number=sample.serial_number,
            results=[_result_read(result, specs[result.specification_id]) for result in sample.results],
        )
        for sample in sorted(run.samples, key=lambda s: s.sample_sequence)
    ]
    base = _run_read(run)
    return MeasurementRunDetailRead(**base.model_dump(), samples=samples_read)


@router.get("/characteristics/{characteristic_id}/series", response_model=SeriesResponse)
def get_characteristic_series(
    characteristic_id: uuid.UUID,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    max_points: int = Query(default=DEFAULT_MAX_POINTS, ge=1, le=HARD_MAX_POINTS),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("measurement.measurement_result", "read")),
) -> SeriesResponse:
    characteristic = db.get(Characteristic, characteristic_id)
    if characteristic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Characteristic not found.")

    # Uses the (characteristic_id, measured_at) index (migration 0003) for
    # both the range filter and the ORDER BY -- verified with EXPLAIN
    # against the full seed dataset (see this PR's description).
    stmt = (
        select(MeasurementResult, MeasurementSample.sample_sequence, Specification)
        .join(MeasurementSample, MeasurementResult.measurement_sample_id == MeasurementSample.id)
        .join(Specification, MeasurementResult.specification_id == Specification.id)
        .where(MeasurementResult.characteristic_id == characteristic_id)
    )
    if from_ is not None:
        stmt = stmt.where(MeasurementResult.measured_at >= from_)
    if to is not None:
        stmt = stmt.where(MeasurementResult.measured_at <= to)
    stmt = stmt.order_by(MeasurementResult.measured_at)

    rows = db.execute(stmt).all()
    total_points = len(rows)

    selected = rows
    downsampled = False
    if total_points > max_points:
        downsampled = True
        step = total_points / max_points
        indices = sorted({min(int(i * step), total_points - 1) for i in range(max_points)})
        indices[-1] = total_points - 1
        selected = [rows[i] for i in indices]

    points = [
        SeriesPoint(
            result_id=result.id,
            measured_at=result.measured_at,
            value=result.value,
            deviation=_compute_deviation_and_ok(result.value, spec)[0],
            is_ok=_compute_deviation_and_ok(result.value, spec)[1],
            sample_index=sample_sequence,
            specification=_specification_snapshot(spec),
        )
        for result, sample_sequence, spec in selected
    ]

    return SeriesResponse(
        characteristic_id=characteristic_id,
        unit=characteristic.unit,
        total_points=total_points,
        returned_points=len(points),
        downsampled=downsampled,
        points=points,
    )


DEFAULT_CAPABILITY_WINDOW_SIZE = 20
MAX_CAPABILITY_WINDOW_SIZE = 500


@router.get(
    "/characteristics/{characteristic_id}/capability-history",
    response_model=CapabilityHistoryResponse,
)
def get_capability_history(
    characteristic_id: uuid.UUID,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    window_size: int = Query(default=DEFAULT_CAPABILITY_WINDOW_SIZE, ge=2, le=MAX_CAPABILITY_WINDOW_SIZE),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("measurement.measurement_result", "read")),
) -> CapabilityHistoryResponse:
    """LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md): Cpk/control-limit
    history over a date range, windowed by point count. Same RBAC as
    `/series` (no new permission) -- this is the same measurement-result data,
    just aggregated."""
    characteristic = db.get(Characteristic, characteristic_id)
    if characteristic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Characteristic not found.")

    windows = compute_capability_history(db, characteristic_id, from_=from_, to=to, window_size=window_size)
    return CapabilityHistoryResponse(
        characteristic_id=characteristic_id,
        unit=characteristic.unit,
        window_size=window_size,
        windows=[CapabilityWindowRead.model_validate(window) for window in windows],
    )


@router.get(
    "/characteristics/{characteristic_id}/experimental-drift",
    response_model=ExperimentalDriftRead | None,
)
def get_experimental_drift(
    characteristic_id: uuid.UUID,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    window_size: int = Query(default=DEFAULT_CAPABILITY_WINDOW_SIZE, ge=2, le=MAX_CAPABILITY_WINDOW_SIZE),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("measurement.measurement_result", "read")),
) -> ExperimentalDriftRead | None:
    """Phase 13 preview (CLAUDE.md §22): a real, shadow-mode CUSUM drift
    detector over the same Cpk-window series `/capability-history` returns.
    Read-only, no side effects -- never writes an Alert/Recommendation, same
    RBAC as `/capability-history` (no new permission)."""
    characteristic = db.get(Characteristic, characteristic_id)
    if characteristic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Characteristic not found.")

    result = compute_experimental_drift(db, characteristic_id, from_=from_, to=to, window_size=window_size)
    return ExperimentalDriftRead.model_validate(result) if result is not None else None


@router.get(
    "/characteristics/{characteristic_id}/sampling-recommendation",
    response_model=SamplingRecommendation,
)
def get_sampling_recommendation(
    characteristic_id: uuid.UUID,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    window_size: int = Query(default=DEFAULT_CAPABILITY_WINDOW_SIZE, ge=2, le=MAX_CAPABILITY_WINDOW_SIZE),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("measurement.measurement_result", "read")),
) -> SamplingRecommendation:
    """EXPERIMENTAL (see app.services.adaptive_sampling_service): a
    Thompson-Sampling-based adaptive inspection sampling frequency
    recommendation over the same Cpk-window series `/capability-history`
    returns, cross-checked against the real Recommendation table for this
    characteristic. Read-only, purely advisory -- never writes an Alert/
    Recommendation/Decision, never overrides the rule-based system. Same
    RBAC as `/capability-history` and `/recommendations` (identical
    {metrologist, quality_engineer, admin, auditor} read role set per
    docs/security/rbac.md -- no new permission, same precedent as
    `/experimental-drift`). Fewer than the engine's minimum window count is
    NOT a 404/error: the response body carries a conservative default
    frequency with low confidence instead."""
    characteristic = db.get(Characteristic, characteristic_id)
    if characteristic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Characteristic not found.")
    return compute_adaptive_sampling_recommendation(
        db, characteristic_id, from_=from_, to=to, window_size=window_size
    )
