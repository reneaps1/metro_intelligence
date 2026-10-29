"""IQ-F14: line quality panel (industrial edition only, `docs/design/line-quality-panel.md`).

- `GET /line-panel/moments`: notable moments of the whole line sequence of a
  dataset (longest NOK streaks, strongest attention alarms, longest calm
  stretches), the presenter's jump targets.
- `GET /line-panel/replay`: a window of pieces (plus lead pieces) with the
  per-piece rule state of the `line_alarm_engine` and every alarm active in it,
  so the frontend replays the line piece by piece.

Datasets: the SIMULATED dimensional dataset (machine filter, default the first
machine) and the customer's REAL dataset when it is configured locally (plan
decision D8; it has no machines, so `machine` is ignored). Anything else: 404.

Read-only and stateless, shadow mode: alarms ask a person for an action and are
never persisted; acknowledgements in the replay live in the browser only.
RBAC reuses `measurement.measurement_result:read`, like the F5 quality analytics.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.edition import require_industrial_edition
from app.core.security import require_permission
from app.engines.line_alarms.rules import ENGINE_NAME, ENGINE_VERSION, LineAlarm
from app.engines.quality_analytics.dataset import DimensionalDataset
from app.engines.quality_analytics.synthetic import SYNTHETIC_DATASET_ID, synthetic_dataset
from app.models.security import User
from app.schemas.line_panel import (
    AlarmOut,
    BaselineOut,
    LineOut,
    MomentOut,
    MomentsResponse,
    PiecesOut,
    ReplayResponse,
    RulesOut,
    RuleTexts,
    ShiftOut,
    StateOut,
    StationOut,
    WindowOut,
)
from app.services.line_panel_service import (
    LinePanel,
    StartOutsideDataError,
    UnknownMachineError,
    line_panel,
    replay_window,
)
from app.services.real_dataset_service import REAL_DATASET_ID, load_real_dataset

router = APIRouter(
    prefix="/line-panel",
    tags=["line-panel"],
    dependencies=[Depends(require_industrial_edition)],
)

_read_quality = require_permission("measurement.measurement_result", "read")

DatasetId = Query(SYNTHETIC_DATASET_ID, max_length=128)
MachineCode = Query(None, max_length=32)


def _dataset(dataset: str) -> DimensionalDataset:
    if dataset == SYNTHETIC_DATASET_ID:
        return synthetic_dataset()
    if dataset == REAL_DATASET_ID:
        real = load_real_dataset()
        if real is not None:
            return real
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset not found.")


def _panel(dataset: str, machine: str | None) -> LinePanel:
    ds = _dataset(dataset)
    try:
        return line_panel(ds, machine)
    except UnknownMachineError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown machine.") from None


def _pct(rate: float) -> str:
    return f"{rate * 100:.1f} %"


def _rules(panel: LinePanel) -> RulesOut:
    ev = panel.evaluation
    c = ev.config
    return RulesOut(
        run_limit=c.run_limit,
        nest_window=c.nest_window,
        nest_factor=c.nest_factor,
        nest_min_nok=c.nest_min_nok,
        rate_window=c.rate_window,
        rate_factor=c.rate_factor,
        rate_limit=round(ev.rate_limit, 6),
        cavity_window=c.cavity_window,
        cavity_factor=c.cavity_factor,
        cavity_limit=round(ev.cavity_limit, 6),
        reference_nok_rate=round(ev.reference_nok_rate, 6),
        clear_fraction=c.clear_fraction,
        texts=RuleTexts(
            R1=(
                f"{c.run_limit} NOK consecutivas en la línea → parar la línea y segregar desde la "
                "primera NOK de la racha."
            ),
            R2=(
                f"Un nido con tasa NOK ≥ {c.nest_factor:g}× la del resto de nidos en sus últimas "
                f"{c.nest_window} piezas (mínimo {c.nest_min_nok} NOK) → revisar pines y localizador "
                "de ese nido; bloquear el nido si persiste."
            ),
            R3=(
                f"Tasa NOK de las últimas {c.rate_window} piezas ≥ {c.rate_factor:g}× la referencia "
                f"histórica ({_pct(ev.reference_nok_rate)}) → llamar a calidad y revisar la primera "
                "estación que falla."
            ),
            R4=(
                f"Cavidad de molde con tasa NOK ≥ {c.cavity_factor:g}× la referencia en sus últimas "
                f"{c.cavity_window} piezas → revisión de herramental en el próximo cambio, sin parar."
            ),
        ),
    )


def _value(rule: str, v: float) -> float:
    # Streaks are counts, R2 is a ratio, R3/R4 are rates.
    return round(v, 3) if rule == "R2" else round(v, 4)


def _alarm(alarm_id: str, a: LineAlarm) -> AlarmOut:
    return AlarmOut(
        id=alarm_id,
        rule=a.rule,
        priority=a.priority,
        key=a.key,
        raised_index=a.raised_index,
        raised_ts=a.raised_ts,
        cleared_index=a.cleared_index,
        cleared_ts=a.cleared_ts,
        evidence_from_index=a.evidence_from_index,
        evidence_from_ts=a.evidence_from_ts,
        value=_value(a.rule, a.value),
        peak=_value(a.rule, a.peak),
        limit=round(a.limit, 6),
        nests=list(a.nests),
        station=a.station,
    )


@router.get("/moments", response_model=MomentsResponse)
def read_moments(
    dataset: str = DatasetId,
    machine: str | None = MachineCode,
    _user: User = Depends(_read_quality),
) -> MomentsResponse:
    panel = _panel(dataset, machine)
    ds, ts = panel.dataset, panel.line.timestamps
    return MomentsResponse(
        dataset=ds.id,
        dataset_name=ds.name,
        provenance=panel.provenance,
        utc_offset_minutes=ds.utc_offset_s // 60,
        start_ts=ts[0] if ts else 0.0,
        end_ts=ts[-1] if ts else 0.0,
        pieces=len(ts),
        reference_nok_rate=round(panel.evaluation.reference_nok_rate, 6),
        engine_name=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        moments=[
            MomentOut(
                key=m.key,
                kind=m.kind,
                rule=m.rule,
                key_group=m.key_group,
                raised_ts=m.raised_ts,
                peak=_value(m.rule or "", m.peak),
                label=m.label,
                replay_start_ts=m.replay_start_ts,
            )
            for m in panel.moments
        ],
    )


@router.get("/replay", response_model=ReplayResponse)
def read_replay(
    dataset: str = DatasetId,
    machine: str | None = MachineCode,
    start: float | None = Query(None, description="Window start (epoch s); default: first piece."),
    minutes: int = Query(60, ge=5, le=240),
    _user: User = Depends(_read_quality),
) -> ReplayResponse:
    panel = _panel(dataset, machine)
    try:
        r = replay_window(panel, start, minutes)
    except StartOutsideDataError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Start is outside the data."
        ) from None
    ds, line = panel.dataset, panel.line
    molds = line.mold_cavities
    b = r.baseline
    return ReplayResponse(
        engine_name=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        dataset=ds.id,
        dataset_name=ds.name,
        provenance=panel.provenance,
        nok_basis=ds.nok_basis,
        utc_offset_minutes=ds.utc_offset_s // 60,
        machine=line.machine,
        line=LineOut(
            nests=ds.distinct(line.nests),
            mold_cavities=None if molds is None else len(ds.distinct(molds)),
            stations=[StationOut(key=s.key, name=s.name) for s in ds.stations],
        ),
        rules=_rules(panel),
        window=WindowOut(start_ts=r.start_ts, end_ts=r.end_ts),
        lead=r.lead,
        shifts=[ShiftOut(label=s.label, start_ts=s.start_ts, end_ts=s.end_ts) for s in r.shifts],
        baseline=BaselineOut(
            pieces=b.pieces,
            nok=b.nok,
            by_nest=b.by_nest,
            by_cavity=b.by_cavity,
            by_station=b.by_station,
            hours=b.hours,
        ),
        pieces=PiecesOut(t=r.t, nest=r.nest, cavity=r.cavity, nok=r.nok, station=r.station),
        state=StateOut(
            run=r.run,
            rate=r.rate,
            nest_ratio=r.nest_ratio,
            nest_ratio_nest=r.nest_ratio_nest,
            cavity_rate=r.cavity_rate,
            cavity_worst=r.cavity_worst,
        ),
        alarms=[_alarm(alarm_id, a) for alarm_id, a in r.alarms],
    )
