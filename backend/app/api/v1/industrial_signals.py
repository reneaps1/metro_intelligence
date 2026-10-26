"""IQ-F2: read-only API over the simulated process-signal generator
(`app.engines.process_simulation`).

Industrial edition only: the router-level `require_industrial_edition`
dependency makes every route 404 in the metrology edition.

RBAC: reuses the `live_monitor.stream` permission (plan decision D4) -- this
is the same kind of resource as the Live Monitor replay (read-only, replayed
or simulated data, never written to measurement history), so it gets the same
role set (metrologist, quality engineer, admin, auditor) without a migration.

Every payload carries `source_type="SIMULATED"`: nothing here was measured.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.edition import require_industrial_edition
from app.core.security import require_permission
from app.engines.process_simulation import (
    GENERATOR_VERSION,
    MACHINES,
    SCENARIO_DURATION_S,
    SCENARIO_START,
    SCENARIOS,
    build_tree,
    generate_series,
    get_scenario,
    parse_signal_id,
    scenario_events,
    signal_id,
)
from app.engines.process_simulation.alignment import (
    DEFAULT_CYCLE_LAGS,
    DEFAULT_TIME_LAGS_S,
    correlate,
)
from app.models.security import User
from app.schemas.industrial_signals import (
    CorrelationResponse,
    CorrelationSignal,
    LagScoreOut,
    ProcessEventListResponse,
    ProcessEventOut,
    ScenarioListResponse,
    ScenarioOut,
    SeriesResponse,
    SignalSeries,
    SignalTreeNode,
    SignalTreeResponse,
)

router = APIRouter(
    prefix="/industrial-signals",
    tags=["industrial-signals"],
    dependencies=[Depends(require_industrial_edition)],
)

_read = require_permission("live_monitor", "stream")

MAX_SIGNALS_PER_REQUEST = 12
MIN_POINTS = 50
MAX_POINTS = 5000
DEFAULT_POINTS = 1500

MAX_TIME_LAG_S = 3600.0
MAX_CYCLE_LAG = 50

_SCENARIO_END = SCENARIO_START + timedelta(seconds=SCENARIO_DURATION_S)
_PRIMARY_MACHINE = next(m.code for m in MACHINES if m.primary)


def _scenario_or_404(scenario_id: str) -> None:
    try:
        get_scenario(scenario_id)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Scenario not found.") from None


def _offset(dt: datetime | None, default: float) -> float:
    if dt is None:
        return default
    if dt.tzinfo is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Timestamps must include a timezone."
        )
    return min(max((dt - SCENARIO_START).total_seconds(), 0.0), SCENARIO_DURATION_S)


def _at(offset_s: float) -> datetime:
    return SCENARIO_START + timedelta(seconds=offset_s)


def _epoch_ms(offset_s: float) -> int:
    return round((SCENARIO_START.timestamp() + offset_s) * 1000)


@router.get("/tree", response_model=SignalTreeResponse)
def read_signal_tree(_user: User = Depends(_read)) -> SignalTreeResponse:
    return SignalTreeResponse(
        source_type="SIMULATED",
        generator_version=GENERATOR_VERSION,
        root=SignalTreeNode.model_validate(build_tree()),
    )


@router.get("/scenarios", response_model=ScenarioListResponse)
def list_scenarios(_user: User = Depends(_read)) -> ScenarioListResponse:
    return ScenarioListResponse(
        source_type="SIMULATED",
        generator_version=GENERATOR_VERSION,
        items=[
            ScenarioOut(
                id=s.id,
                name=s.name,
                description=s.description,
                start=SCENARIO_START,
                end=_SCENARIO_END,
                event_count=len(s.events),
            )
            for s in SCENARIOS
        ],
    )


@router.get("/series", response_model=SeriesResponse)
def read_series(
    scenario: str = Query(..., max_length=64),
    signals: str = Query(..., max_length=1024, description="Comma-separated signal ids"),
    start: datetime | None = None,
    end: datetime | None = None,
    max_points: int = Query(DEFAULT_POINTS, ge=MIN_POINTS, le=MAX_POINTS),
    _user: User = Depends(_read),
) -> SeriesResponse:
    _scenario_or_404(scenario)
    ids = list(dict.fromkeys(s.strip() for s in signals.split(",") if s.strip()))
    if not ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one signal is required.")
    if len(ids) > MAX_SIGNALS_PER_REQUEST:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"At most {MAX_SIGNALS_PER_REQUEST} signals per request.",
        )
    for sid in ids:
        try:
            parse_signal_id(sid)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Signal not found.") from None

    start_s = _offset(start, 0.0)
    end_s = _offset(end, SCENARIO_DURATION_S)
    if start_s >= end_s:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested window is empty or outside the scenario.",
        )

    series = []
    for sid in ids:
        result = generate_series(scenario, sid, start_s, end_s, max_points)
        series.append(
            SignalSeries(
                signal_id=sid,
                name=result.signal.name,
                unit=result.signal.unit,
                value_type=result.signal.value_type,
                sampling=result.signal.sampling,
                native_points=result.native_points,
                returned_points=len(result.points),
                downsampled=result.downsampled,
                mode=result.mode,
                points=[(_epoch_ms(t), round(v, 4)) for t, v in result.points],
            )
        )
    return SeriesResponse(
        scenario_id=scenario,
        source_type="SIMULATED",
        generator_version=GENERATOR_VERSION,
        start=_at(start_s),
        end=_at(end_s),
        series=series,
    )


@router.get("/events", response_model=ProcessEventListResponse)
def list_events(
    scenario: str = Query(..., max_length=64),
    start: datetime | None = None,
    end: datetime | None = None,
    _user: User = Depends(_read),
) -> ProcessEventListResponse:
    _scenario_or_404(scenario)
    start_s = _offset(start, 0.0)
    end_s = _offset(end, SCENARIO_DURATION_S)
    items = []
    for index, event in enumerate(scenario_events(scenario)):
        event_end = event.offset_s + (event.duration_s or 0.0)
        if event_end < start_s or event.offset_s > end_s:
            continue
        items.append(
            ProcessEventOut(
                id=f"{scenario}-{index:02d}",
                scenario_id=scenario,
                machine_code=_PRIMARY_MACHINE,
                event_type=event.event_type,
                label=event.label,
                severity=event.severity,
                start=_at(event.offset_s),
                end=_at(event_end) if event.duration_s is not None else None,
                signal_ids=[signal_id(_PRIMARY_MACHINE, key) for key in event.signal_keys],
            )
        )
    return ProcessEventListResponse(scenario_id=scenario, source_type="SIMULATED", items=items)


@router.get("/correlation", response_model=CorrelationResponse)
def read_correlation(
    scenario: str = Query(..., max_length=64),
    x: str = Query(..., max_length=128),
    y: str = Query(..., max_length=128),
    mode: Literal["time", "cycle"] = "cycle",
    lag: float = 0.0,
    scan: bool = True,
    start: datetime | None = None,
    end: datetime | None = None,
    _user: User = Depends(_read),
) -> CorrelationResponse:
    """Pair two channels and fit y = intercept + slope * x (IQ-F4).

    ``lag`` is in seconds for ``mode=time`` and in cycles for ``mode=cycle``;
    with ``scan`` the Pearson r over a range of lags is returned as well.
    """
    _scenario_or_404(scenario)
    try:
        _, x_signal = parse_signal_id(x)
        _, y_signal = parse_signal_id(y)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Signal not found.") from None

    if mode == "cycle":
        if lag != int(lag) or abs(lag) > MAX_CYCLE_LAG:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"In cycle mode the lag must be a whole number of cycles up to ±{MAX_CYCLE_LAG}.",
            )
    elif abs(lag) > MAX_TIME_LAG_S:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"The lag must be within ±{int(MAX_TIME_LAG_S)} s."
        )

    start_s = _offset(start, 0.0)
    end_s = _offset(end, SCENARIO_DURATION_S)
    if start_s >= end_s:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The requested window is empty or outside the scenario.",
        )

    scan_lags = (DEFAULT_CYCLE_LAGS if mode == "cycle" else DEFAULT_TIME_LAGS_S) if scan else None
    try:
        result = correlate(scenario, x, y, start_s, end_s, mode, lag, scan_lags)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cycle alignment needs both signals from the same machine.",
        ) from None

    fit = result.fit
    return CorrelationResponse(
        scenario_id=scenario,
        source_type="SIMULATED",
        generator_version=GENERATOR_VERSION,
        x=CorrelationSignal(
            signal_id=x, name=x_signal.name, unit=x_signal.unit, causal_imposed=x_signal.causal_imposed
        ),
        y=CorrelationSignal(
            signal_id=y, name=y_signal.name, unit=y_signal.unit, causal_imposed=y_signal.causal_imposed
        ),
        mode=mode,
        lag=result.lag,
        lag_unit="cycles" if mode == "cycle" else "s",
        start=_at(start_s),
        end=_at(end_s),
        n=fit.n,
        pearson_r=fit.pearson_r,
        slope=fit.slope,
        intercept=fit.intercept,
        r_squared=fit.r_squared,
        points=[(round(a, 6), round(b, 6)) for a, b in result.pairs],
        lag_scan=[LagScoreOut(lag=s.lag, n=s.n, pearson_r=s.pearson_r) for s in result.scan],
        best_lag=result.best_lag,
        causal_imposed=result.causal_imposed,
    )
