"""IQ-F5: read-only dimensional quality analytics (industrial edition only).

Aggregations run over a `DimensionalDataset`: the synthetic demo dataset, the
customer's REAL dataset when configured locally (IQ-F10,
`services/real_dataset_service.py`), or one the current user built from a CSV
(IQ-F6, `quality_imports.py`; held in memory, visible only to its owner). Every payload carries the dataset's
`source_type` so the UI can label it.

RBAC: `measurement.measurement_result.read` -- these are aggregates of
measurement results, the same data the measurements API already exposes.

IQ-F19: `/xy` returns the X/Y deviation cloud of one pin pair against its
position tolerance (`engines/quality_analytics/position.py`).

IQ-F13: `/process-join` ("Vista A") joins the REAL pieces by time with the
SIMULATED process of the `real_calendar` scenario
(`services/process_join_service.py`); REAL dataset only, 404 without it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.edition import require_industrial_edition
from app.core.security import require_permission
from app.engines.process_simulation.generator import GENERATOR_VERSION
from app.engines.quality_analytics import (
    SYNTHETIC_DATASET_ID,
    DimensionalDataset,
    QualityFilter,
    overview,
    synthetic_dataset,
    variable_detail,
)
from app.engines.quality_analytics.position import xy_detail
from app.models.security import User
from app.schemas.quality_analytics import (
    DatasetListResponse,
    DatasetOut,
    OverviewResponse,
    PinPairOut,
    PresetOut,
    ProcessJoinBucket,
    ProcessJoinLag,
    ProcessJoinResponse,
    ProcessJoinSignal,
    ReportSummary,
    StationOut,
    VariableDetailResponse,
    XYDetailResponse,
)
from app.services.imported_dataset_store import get_imported_dataset_store
from app.services.process_join_service import (
    DEFAULT_BUCKET_MINUTES,
    join_signal,
    process_join,
    validate_window,
)
from app.services.real_dataset_service import REAL_DATASET_ID, cached_overview, load_real_dataset
from app.services.real_predictive_service import TOTAL_TARGET, target_label, validate_target
from app.services.report_summary_service import load_report_summary

router = APIRouter(
    prefix="/quality-analytics",
    tags=["quality-analytics"],
    dependencies=[Depends(require_industrial_edition)],
)

_read = require_permission("measurement.measurement_result", "read")


def _dataset_or_404(dataset_id: str, user: User) -> DimensionalDataset:
    if dataset_id == SYNTHETIC_DATASET_ID:
        return synthetic_dataset()
    if dataset_id == REAL_DATASET_ID:
        real = load_real_dataset()
        if real is not None:
            return real
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    stored = get_imported_dataset_store().get(dataset_id, user.id)
    if stored is not None:
        return stored.dataset
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset not found.")


def _csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    return items or None


def _epoch(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Timestamps must include a timezone."
        )
    return dt.timestamp()


def _filter(
    ds: DimensionalDataset,
    start: datetime | None,
    end: datetime | None,
    machines: str | None,
    cavities: str | None,
    shifts: str | None,
    batches: str | None,
    variables: str | None,
    mold_cavities: str | None = None,
    stations: str | None = None,
    exclude_flags: int = 0,
) -> QualityFilter:
    cavity_set = _int_set(cavities, "Cavities must be integers.")
    mold_set = _int_set(mold_cavities, "Mold cavities must be integers.")
    station_keys = _csv(stations)
    if station_keys and any(k not in {s.key for s in ds.stations} for k in station_keys):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown station.")
    variable_keys = _csv(variables)
    known = {v.key for v in ds.variables}
    if variable_keys and any(k not in known for k in variable_keys):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown variable.")
    machine_values, shift_values, batch_values = _csv(machines), _csv(shifts), _csv(batches)
    return QualityFilter(
        start=_epoch(start),
        end=_epoch(end),
        machines=frozenset(machine_values) if machine_values else None,
        cavities=cavity_set,
        shifts=frozenset(shift_values) if shift_values else None,
        batches=frozenset(batch_values) if batch_values else None,
        variables=tuple(variable_keys) if variable_keys else None,
        mold_cavities=mold_set,
        stations=tuple(station_keys) if station_keys else None,
        exclude_flags=exclude_flags,
    )


def _int_set(value: str | None, message: str) -> frozenset[int] | None:
    items = _csv(value)
    try:
        return frozenset(int(c) for c in items) if items else None
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from None


def dataset_out(ds: DimensionalDataset) -> DatasetOut:
    return DatasetOut(
        id=ds.id,
        name=ds.name,
        description=ds.description,
        source_type=ds.source_type,
        period_start=datetime.fromtimestamp(ds.timestamps[0], tz=UTC),
        period_end=datetime.fromtimestamp(ds.timestamps[-1], tz=UTC),
        pieces=len(ds),
        groups=len(set(ds.group_ids)) if ds.has_groups else len(ds),
        variables=[
            {
                "key": v.key,
                "name": v.name,
                "unit": v.unit,
                "nominal": v.display_nominal,
                "lsl": v.lsl,
                "usl": v.usl,
            }
            for v in ds.variables
        ],
        mold_cavities=ds.distinct(ds.mold_cavities) if ds.mold_cavities is not None else [],
        stations=[StationOut(key=s.key, name=s.name) for s in ds.stations],
        nok_basis=ds.nok_basis,
        utc_offset_minutes=ds.utc_offset_s // 60,
        has_groups=ds.has_groups,
        presets=[
            PresetOut(key=p.key, label=p.label, stations=list(p.stations), group_by=p.group_by)
            for p in ds.presets
        ],
        data_quality=ds.data_quality,
        machines=ds.distinct(ds.machines),
        cavities=ds.distinct(ds.cavities),
        shifts=ds.distinct(ds.shifts),
        batches=ds.distinct(ds.batches),
        available_filters=ds.available_filters(),
        mechanisms=ds.mechanisms,
        has_reported_verdict=ds.reported_nok is not None,
        pin_pairs=[PinPairOut(key=p.key, label=p.label) for p in ds.pin_pairs],
    )


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(user: User = Depends(_read)) -> DatasetListResponse:
    imported = [dataset_out(item.dataset) for item in get_imported_dataset_store().list_for(user.id)]
    real = load_real_dataset()
    leading = [dataset_out(real)] if real is not None else []
    return DatasetListResponse(items=[*leading, dataset_out(synthetic_dataset()), *imported])


@router.get("/overview", response_model=OverviewResponse)
def read_overview(
    dataset: str = Query(SYNTHETIC_DATASET_ID, max_length=128),
    start: datetime | None = None,
    end: datetime | None = None,
    machines: str | None = Query(None, max_length=512),
    cavities: str | None = Query(None, max_length=512),
    shifts: str | None = Query(None, max_length=128),
    batches: str | None = Query(None, max_length=512),
    variables: str | None = Query(None, max_length=2048),
    granularity: Literal["day", "hour", "shift"] = "day",
    mold_cavities: str | None = Query(None, max_length=512),
    stations: str | None = Query(None, max_length=512),
    exclude_flags: int = Query(0, ge=0, le=255),
    user: User = Depends(_read),
) -> OverviewResponse:
    ds = _dataset_or_404(dataset, user)
    f = _filter(
        ds, start, end, machines, cavities, shifts, batches, variables, mold_cavities, stations, exclude_flags
    )
    result = cached_overview(ds, f, granularity) if ds.source_type == "REAL" else overview(ds, f, granularity)
    return OverviewResponse(dataset_id=ds.id, source_type=ds.source_type, granularity=granularity, **result)


@router.get("/variable", response_model=VariableDetailResponse)
def read_variable(
    variable: str = Query(..., max_length=128),
    dataset: str = Query(SYNTHETIC_DATASET_ID, max_length=128),
    group_by: Literal["cavity", "machine", "shift", "batch", "mold_cavity"] = "cavity",
    start: datetime | None = None,
    end: datetime | None = None,
    machines: str | None = Query(None, max_length=512),
    cavities: str | None = Query(None, max_length=512),
    shifts: str | None = Query(None, max_length=128),
    batches: str | None = Query(None, max_length=512),
    mold_cavities: str | None = Query(None, max_length=512),
    exclude_flags: int = Query(0, ge=0, le=255),
    user: User = Depends(_read),
) -> VariableDetailResponse:
    ds = _dataset_or_404(dataset, user)
    if variable not in {v.key for v in ds.variables}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Variable not found.")
    if group_by == "mold_cavity" and ds.mold_cavities is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dataset has no mold cavities.")
    f = _filter(ds, start, end, machines, cavities, shifts, batches, None, mold_cavities, None, exclude_flags)
    detail = variable_detail(ds, f, variable, group_by)
    return VariableDetailResponse(dataset_id=ds.id, source_type=ds.source_type, **detail)


@router.get("/xy", response_model=XYDetailResponse)
def read_xy(
    pair: str = Query(..., max_length=64),
    dataset: str = Query(SYNTHETIC_DATASET_ID, max_length=128),
    group_by: Literal["nok", "nest", "mold_cavity"] = "nok",
    start: datetime | None = None,
    end: datetime | None = None,
    machines: str | None = Query(None, max_length=512),
    cavities: str | None = Query(None, max_length=512),
    shifts: str | None = Query(None, max_length=128),
    batches: str | None = Query(None, max_length=512),
    variables: str | None = Query(None, max_length=2048),
    mold_cavities: str | None = Query(None, max_length=512),
    stations: str | None = Query(None, max_length=512),
    exclude_flags: int = Query(0, ge=0, le=255),
    user: User = Depends(_read),
) -> XYDetailResponse:
    ds = _dataset_or_404(dataset, user)
    if pair not in {p.key for p in ds.pin_pairs}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Pin pair not found.")
    if group_by == "mold_cavity" and ds.mold_cavities is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dataset has no mold cavities.")
    f = _filter(
        ds, start, end, machines, cavities, shifts, batches, variables, mold_cavities, stations, exclude_flags
    )
    detail = xy_detail(ds, f, pair, group_by)
    return XYDetailResponse(dataset_id=ds.id, source_type=ds.source_type, **detail)


@router.get("/report-summary", response_model=ReportSummary)
def read_report_summary(_user: User = Depends(_read)) -> ReportSummary:
    return load_report_summary()


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.get("/process-join", response_model=ProcessJoinResponse)
def read_process_join(
    signal: str = Query(..., max_length=128),
    dataset: str = Query(REAL_DATASET_ID, max_length=128),
    target: str = Query(TOTAL_TARGET, max_length=64),
    bucket_minutes: int = DEFAULT_BUCKET_MINUTES,
    lag_minutes: int = 0,
    _user: User = Depends(_read),
) -> ProcessJoinResponse:
    """Vista A: NOK rate of the REAL pieces vs. a SIMULATED signal of the calendar scenario, per bucket.

    ``lag_minutes`` > 0 pairs each bucket with the cycles that started that
    long before it (the process precedes the inspection).
    """
    real = load_real_dataset() if dataset == REAL_DATASET_ID else None
    if real is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    try:
        join_signal(signal)
    except ValueError:
        raise _unprocessable("Unknown signal or not offered by the process join.") from None
    try:
        validate_target(real, target)
    except ValueError:
        raise _unprocessable("Unknown target.") from None
    try:
        validate_window(bucket_minutes, lag_minutes)
    except ValueError:
        raise _unprocessable(
            "bucket_minutes must be 15, 30 or 60 and lag_minutes a multiple of it within ±180."
        ) from None

    result = process_join(real, signal, target, bucket_minutes, lag_minutes)
    fit = result.join.fit
    return ProcessJoinResponse(
        dataset=real.id,
        scenario_id=result.scenario.id,
        generator_version=GENERATOR_VERSION,
        signal=ProcessJoinSignal(id=signal, name=result.signal_name, unit=result.signal.unit),
        target=target,
        target_label=target_label(real, target),
        bucket_minutes=bucket_minutes,
        lag_minutes=lag_minutes,
        utc_offset_minutes=real.utc_offset_s // 60,
        n=fit.n,
        pearson_r=fit.pearson_r,
        slope=fit.slope,
        intercept=fit.intercept,
        r_squared=fit.r_squared,
        buckets=[
            ProcessJoinBucket(start_ts=b.start_ts, x=b.x, y=b.y, pieces=b.pieces, cycles=b.cycles)
            for b in result.join.buckets
        ],
        lag_scan=[ProcessJoinLag(lag_minutes=lag, r=s.r, n=s.n) for lag, s in result.scan],
        best_lag_minutes=result.best_lag_minutes,
        causal_imposed=result.causal_imposed,
        provenance=["REAL", "SIMULATED", "EXPERIMENTAL"],
        notes=result.notes,
    )
