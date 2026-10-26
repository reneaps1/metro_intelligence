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
from app.models.security import User
from app.schemas.industrial_signals import (
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
