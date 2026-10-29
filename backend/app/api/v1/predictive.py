"""IQ-F7: predictive lab for demo step 6 (industrial edition only).

- `GET /predictive/model-lab`: PRECOMPUTED results of a closed historical
  ML/DL study (private file or illustrative placeholder, decision D1).
- `GET /predictive/nok-waves`: EXPERIMENTAL persistence rule evaluated per
  episode against the waves injected in the SIMULATED dimensional dataset.
- `GET /predictive/cusum`: shadow-mode CUSUM over an hourly series of that dataset.
- `GET /predictive/what-if`: HYPOTHETICAL evaluation of the Vista B mechanism.
- `GET /predictive/failure-study` (F7.b): EXPERIMENTAL failure prediction on a
  SIMULATED machine history, with baselines and per-episode evaluation.
- IQ-F12: `nok-waves` and `cusum` also run over the customer's REAL dataset
  (`dataset=real-dimensional`, local only); `group-alarms` (per-cavity/nest
  alarm rule) and `piece-risk` (per-piece risk before inspection) exist only
  for it. Episodes of REAL data are labelled with hindsight, never injected.

Read-only and stateless: nothing raises a real Alert or touches measurement
history. RBAC: the analytics over the dimensional dataset and the study
results reuse `measurement.measurement_result:read` (same as the F5 quality
analytics); the process simulation reuses `live_monitor.stream` (same as
`/industrial-signals`).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.edition import require_industrial_edition
from app.core.security import require_permission
from app.engines.experimental_ml import drift_cusum, group_alarms, nok_waves, piece_risk
from app.engines.experimental_ml.failure_prediction import run_study
from app.engines.process_simulation.what_if import (
    HOLD_RANGE_BAR,
    MOLD_DELTA_RANGE_C,
    what_if,
)
from app.engines.quality_analytics.dataset import DimensionalDataset
from app.engines.quality_analytics.synthetic import MACHINES as DIMENSIONAL_MACHINES
from app.engines.quality_analytics.synthetic import SYNTHETIC_DATASET_ID, synthetic_dataset
from app.models.security import User
from app.schemas.predictive import (
    AlertEventOut,
    CoefficientOut,
    ContributionOut,
    CusumPointOut,
    CusumResponse,
    FailureStudyResponse,
    GroupAlarmOut,
    GroupAlarmResponse,
    ModelLab,
    PieceRiskResponse,
    RiskHourOut,
    ScoreEvalOut,
    SweepPointOut,
    TopKOut,
    WaveEpisodeOut,
    WaveHourOut,
    WaveStudyResponse,
    WaveSummary,
    WhatIfResponse,
)
from app.services.model_lab_service import load_model_lab
from app.services.predictive_service import NOK_RATE_SERIES, CusumStudy, WaveStudy, cusum_study, wave_study
from app.services.real_dataset_service import REAL_DATASET_ID, load_real_dataset
from app.services.real_predictive_service import (
    STATION_PREFIX,
    TOTAL_TARGET,
    group_alarm_study,
    piece_risk_study,
    real_cusum_study,
    real_wave_study,
    series_options,
    target_label,
    validate_target,
)

router = APIRouter(
    prefix="/predictive",
    tags=["predictive"],
    dependencies=[Depends(require_industrial_edition)],
)

_read_quality = require_permission("measurement.measurement_result", "read")
_read_simulation = require_permission("live_monitor", "stream")

MachineCode = Query("INY-01", pattern=r"^INY-0[12]$")
DatasetId = Query(SYNTHETIC_DATASET_ID, max_length=128)
TargetQuery = Query(TOTAL_TARGET, max_length=64)
# Synthetic series keep their F7 limits; REAL series have one piece per group.
SYNTHETIC_LIMITS = {"window": 50, "threshold": 100, "horizon": 60}


def _real(dataset: str) -> DimensionalDataset | None:
    """None for the synthetic dataset, the REAL dataset when configured, 404 otherwise."""
    if dataset == SYNTHETIC_DATASET_ID:
        return None
    if dataset == REAL_DATASET_ID:
        real = load_real_dataset()
        if real is not None:
            return real
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset not found.")


def _real_only(dataset: str) -> DimensionalDataset:
    real = _real(dataset)
    if real is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only available for the real dataset."
        )
    return real


def _target(ds: DimensionalDataset, target: str) -> str:
    try:
        return validate_target(ds, target)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown target.") from None


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


@router.get("/model-lab", response_model=ModelLab)
def read_model_lab(_user: User = Depends(_read_quality)) -> ModelLab:
    return load_model_lab()


@router.get("/nok-waves", response_model=WaveStudyResponse)
def read_nok_waves(
    machine: str = MachineCode,
    window: int = Query(5, ge=1, le=1000),
    threshold: int = Query(4, ge=1, le=1000),
    horizon: int = Query(15, ge=0, le=1000),
    dataset: str = DatasetId,
    target: str = TargetQuery,
    episode_window: int = Query(100, ge=10, le=1000),
    episode_threshold: int = Query(10, ge=1, le=1000),
    _user: User = Depends(_read_quality),
) -> WaveStudyResponse:
    real = _real(dataset)
    study: WaveStudy
    if real is None:
        limits = {"window": window, "threshold": threshold, "horizon": horizon}
        if any(limits[k] > v for k, v in SYNTHETIC_LIMITS.items()):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Out of range for the synthetic dataset."
            )
        if machine not in DIMENSIONAL_MACHINES:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Machine not found.")
        study = wave_study(machine, window, threshold, horizon)
    else:
        target = _target(real, target)
        if episode_threshold > episode_window:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Episode threshold exceeds its window."
            )
        study = real_wave_study(real, target, window, threshold, horizon, episode_window, episode_threshold)
    unit: Literal["grupos", "piezas"] = "grupos" if real is None else "piezas"
    series, ev = study.series, study.evaluation
    minute = study.group_interval_s / 60

    def ts(i: int) -> float:
        return series[i].ts

    episodes = [
        WaveEpisodeOut(
            start=ts(e.start),
            end=ts(e.end),
            groups=e.end - e.start + 1,
            status=e.status,
            first_alert=None if e.first_alert is None else ts(e.first_alert),
            delay_min=None if e.delay_groups is None else e.delay_groups * minute,
            remaining_share=e.remaining_share,
        )
        for e in ev.episodes
    ]
    false_runs = {
        run
        for run in ev.alert_events
        if not any(run[1] >= ep.start - horizon and run[0] <= ep.end for ep in study.episodes)
    }
    days = (series[-1].ts - series[0].ts) / 86400 if len(series) > 1 else 1.0
    caught = [e for e in ev.episodes if e.status != "missed"]
    if real is None:
        episode_definition = (
            "Episodio = oleada inyectada en el dataset sintético (verdad conocida). Se cuenta "
            f"como anticipado si hay alerta en los {horizon} grupos previos al inicio, detectado "
            "si la primera alerta cae durante la oleada, y no detectado si no hay alerta. Una "
            "alerta fuera de toda oleada es falsa alarma."
        )
    else:
        episode_definition = (
            f"Datos reales sin verdad conocida: un episodio se etiqueta a posteriori cuando las "
            f"{episode_window} piezas siguientes suman al menos {episode_threshold} NOK (se usa el "
            "futuro solo para etiquetar, nunca como entrada de la regla). Anticipado = alerta en las "
            f"{horizon} piezas previas al inicio; detectado = primera alerta durante el episodio; "
            "una alerta fuera de todo episodio es falsa alarma."
        )
    return WaveStudyResponse(
        source_type="SIMULATED" if real is None else "REAL",
        episode_source="injected" if real is None else "retrospective",
        unit=unit,
        target=None if real is None else target,
        utc_offset_minutes=0 if real is None else real.utc_offset_s // 60,
        engine_name=nok_waves.ENGINE_NAME,
        engine_version=nok_waves.ENGINE_VERSION,
        machine=study.machine,
        window=window,
        threshold=threshold,
        horizon_groups=horizon,
        group_interval_min=minute,
        rule=(
            f"Alertar cuando los últimos {window} {'grupos inspeccionados' if real is None else 'piezas'} "
            f"suman al menos {threshold} piezas NOK. Solo usa NOK ya medidos: puede detectar una racha "
            "iniciada, no anticipar su inicio."
        ),
        episode_definition=episode_definition,
        summary=WaveSummary(
            episodes=len(ev.episodes),
            anticipated=ev.anticipated,
            detected=ev.detected,
            missed=ev.missed,
            mean_delay_min=_mean([e.delay_groups * minute for e in caught if e.delay_groups is not None]),
            mean_remaining_share=_mean([e.remaining_share for e in caught if e.remaining_share is not None]),
            alert_events=len(ev.alert_events),
            false_alarm_events=ev.false_alarm_events,
            false_alarms_per_day=ev.false_alarm_events / days,
        ),
        episodes=episodes,
        alert_events=[
            AlertEventOut(start=ts(a), end=ts(b), false_alarm=(a, b) in false_runs)
            for a, b in ev.alert_events
        ],
        hours=[
            WaveHourOut(ts=h.ts, pieces=h.pieces, nok_pieces=h.nok_pieces, in_wave=h.in_wave, alert=h.alert)
            for h in study.hours
        ],
    )


@router.get("/cusum", response_model=CusumResponse)
def read_cusum(
    machine: str = MachineCode,
    series: str = Query("PinPositionY", max_length=64),
    k: float = Query(0.5, ge=0.1, le=2.0),
    h: float = Query(4.0, ge=1.0, le=10.0),
    dataset: str = DatasetId,
    _user: User = Depends(_read_quality),
) -> CusumResponse:
    real = _real(dataset)
    source = synthetic_dataset() if real is None else real
    variables = {v.key: v for v in source.variables}
    study: CusumStudy
    if real is None:
        if series != NOK_RATE_SERIES and series not in variables:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Series not found.")
        study = cusum_study(machine, series, k, h)
    else:
        if series not in series_options(real):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Series not found.")
        study = real_cusum_study(real, series, k, h)
    if series == NOK_RATE_SERIES:
        label, unit = "Tasa NOK horaria", "fracción"
    elif series.startswith(STATION_PREFIX) and real is not None:
        label, unit = f"Tasa NOK horaria · {real.station(series[len(STATION_PREFIX):]).name}", "fracción"
    else:
        label, unit = variables[series].name, variables[series].unit
    r = study.result
    out = CusumResponse(
        source_type="SIMULATED" if real is None else "REAL",
        utc_offset_minutes=0 if real is None else real.utc_offset_s // 60,
        engine_name=drift_cusum.ENGINE_NAME,
        engine_version=drift_cusum.ENGINE_VERSION,
        machine=study.machine,
        series=series,
        series_label=label if label.startswith("Tasa NOK") else f"{label} · media horaria",
        unit=unit,
        k_stdevs=k,
        h_stdevs=h,
        target=None,
        stdev=None,
        k=None,
        h=None,
        drift_detected=False,
        drift_direction=None,
        drift_ts=None,
        rationale="Serie demasiado corta o constante: el CUSUM no aplica.",
        points=[],
    )
    if r is None:
        return out
    return out.model_copy(
        update={
            "target": float(r.target),
            "stdev": float(r.stdev),
            "k": float(r.k),
            "h": float(r.h),
            "drift_detected": r.drift_detected,
            "drift_direction": r.drift_direction,
            "drift_ts": None if r.drift_index is None else study.timestamps[r.drift_index],
            "rationale": r.rationale,
            "points": [
                CusumPointOut(
                    ts=study.timestamps[p.index],
                    value=float(p.value),
                    cusum_high=float(p.cusum_high),
                    cusum_low=float(p.cusum_low),
                )
                for p in r.points
            ],
        }
    )


@router.get("/what-if", response_model=WhatIfResponse)
def read_what_if(
    hold_pressure: float = Query(620.0, ge=HOLD_RANGE_BAR[0], le=HOLD_RANGE_BAR[1]),
    mold_delta: float = Query(0.0, ge=MOLD_DELTA_RANGE_C[0], le=MOLD_DELTA_RANGE_C[1]),
    nest: int | None = Query(None, ge=1, le=12),
    worn_insert: bool = False,
    _user: User = Depends(_read_simulation),
) -> WhatIfResponse:
    r = what_if(hold_pressure, mold_delta, nest, worn_insert)
    return WhatIfResponse(
        hold_pressure_bar=r.hold_pressure_bar,
        mold_delta_c=r.mold_delta_c,
        nest=r.nest,
        worn_insert=r.worn_insert,
        nominal_mm=r.nominal_mm,
        tolerance_mm=r.tolerance_mm,
        mean_mm=r.mean_mm,
        piece_sd_mm=r.piece_sd_mm,
        nok_probability=r.nok_probability,
        reference_nok_probability=r.reference_nok_probability,
        contributions=[ContributionOut(label=c.label, mm=c.mm) for c in r.contributions],
        hold_sweep=[SweepPointOut(x=p.x, nok_probability=p.nok_probability) for p in r.hold_sweep],
        mold_sweep=[SweepPointOut(x=p.x, nok_probability=p.nok_probability) for p in r.mold_sweep],
        mechanism=(
            "Longitud de pines = 12.000 + 0.006·ΔT molde − 0.0006·(P mantenimiento − 620) "
            "+ offset de nido + ruido; tolerancia ±0.050 mm. Mecanismo impuesto en el "
            "simulador (Vista B), no medido en planta."
        ),
        not_modelled=[
            "El tiempo de ciclo no interviene en el mecanismo sintético: no se ofrece como palanca.",
            "Interacciones, histéresis térmica y efectos de material reales no están representados.",
        ],
    )


@router.get("/failure-study", response_model=FailureStudyResponse)
def read_failure_study(_user: User = Depends(_read_simulation)) -> FailureStudyResponse:
    return FailureStudyResponse.model_validate(run_study())


@router.get("/group-alarms", response_model=GroupAlarmResponse)
def read_group_alarms(
    dataset: str = Query(REAL_DATASET_ID, max_length=128),
    grouping: Literal["mold_cavity", "nest"] = "mold_cavity",
    target: str = TargetQuery,
    k: int = Query(6, ge=1, le=200),
    n: int = Query(30, ge=1, le=500),
    scope: Literal["all", "after_longest_gap"] = "after_longest_gap",
    _user: User = Depends(_read_quality),
) -> GroupAlarmResponse:
    real = _real_only(dataset)
    target = _target(real, target)
    if k > n:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="k must not exceed n.")
    try:
        ev, gap, since = group_alarm_study(real, grouping, target, k, n, scope)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Grouping not available.") from None
    unit = "cavidad de molde" if grouping == "mold_cavity" else "nido"
    return GroupAlarmResponse(
        engine_name=group_alarms.ENGINE_NAME,
        engine_version=group_alarms.ENGINE_VERSION,
        grouping=grouping,
        target=target,
        target_label=target_label(real, target),
        k=k,
        n=n,
        scope=scope,
        scope_start=since,
        longest_gap=gap,
        utc_offset_minutes=real.utc_offset_s // 60,
        rule=(
            f"Alarma de una {unit} cuando al menos {k} de sus últimas {n} piezas son NOK. "
            "Solo usa piezas ya inspeccionadas: avisa que la cavidad empezó a fallar, "
            "no anticipa el primer NOK."
        ),
        pieces=ev.pieces,
        nok=ev.nok,
        nok_after_first_alarm=ev.nok_after_first_alarm,
        share_after_first_alarm=ev.nok_after_first_alarm / ev.nok if ev.nok else None,
        groups_alarmed=ev.groups_alarmed,
        first_alarm_ts=ev.first_alarm_ts,
        ok_in_alarm=ev.ok_in_alarm,
        groups=[GroupAlarmOut(**vars(g)) for g in ev.groups],
        limitations=[
            "Evaluación retrospectiva sobre un período cerrado: no prueba cuántas piezas se habrían evitado; "
            "eso depende de reaccionar (ajustar o bloquear la cavidad) y de que la reacción funcione.",
            "NOK posteriores a la primera alarma = lo que una reacción oportuna podría haber protegido, "
            "como cota superior.",
            "Piezas OK durante la alarma = carga de revisión que generaría la regla.",
        ],
    )


def _score(e: piece_risk.ScoreEval) -> ScoreEvalOut:
    return ScoreEvalOut(
        key=e.key, name=e.name, roc_auc=e.roc_auc, pr_auc=e.pr_auc, top=[TopKOut(**vars(t)) for t in e.top]
    )


@router.get("/piece-risk", response_model=PieceRiskResponse)
def read_piece_risk(
    dataset: str = Query(REAL_DATASET_ID, max_length=128),
    target: str = TargetQuery,
    _user: User = Depends(_read_quality),
) -> PieceRiskResponse:
    real = _real_only(dataset)
    target = _target(real, target)
    try:
        study = piece_risk_study(real, target)
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Not enough data for this study."
        ) from None
    best_baseline = max(b.pr_auc for b in study.baselines)
    return PieceRiskResponse(
        engine_name=piece_risk.ENGINE_NAME,
        engine_version=piece_risk.ENGINE_VERSION,
        target=target,
        target_label=target_label(real, target),
        test_day=study.test_day,
        train_pieces=study.train_pieces,
        train_nok=study.train_nok,
        test_pieces=study.test_pieces,
        test_nok=study.test_nok,
        excluded_pieces=study.excluded_pieces,
        prevalence=study.test_nok / study.test_pieces if study.test_pieces else 0.0,
        model=_score(study.model),
        baselines=[_score(b) for b in study.baselines],
        alarm_rule=None if study.alarm_rule is None else TopKOut(**vars(study.alarm_rule)),
        beats_baselines=study.model.pr_auc > best_baseline,
        coefficients=[CoefficientOut(key=key, name=name, value=v) for key, name, v in study.coefficients],
        hours=[RiskHourOut(ts=ts, pieces=n, mean_risk=r, nok_rate=y) for ts, n, r, y in study.hours],
        utc_offset_minutes=real.utc_offset_s // 60,
        limitations=[
            "Entrenado con los días anteriores y probado con el último día de planta; un solo día de prueba "
            "no cubre turnos, lotes ni mantenimiento.",
            "Solo usa información previa a cada pieza (tasas recientes de su cavidad, su nido y la línea); "
            "no hay parámetros de proceso reales.",
            "Sirve para priorizar inspección o contención, no para rechazar automáticamente.",
        ],
    )
