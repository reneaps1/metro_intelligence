"""IQ-F7: predictive lab for demo step 6 (industrial edition only).

- `GET /predictive/model-lab`: PRECOMPUTED results of a closed historical
  ML/DL study (private file or illustrative placeholder, decision D1).
- `GET /predictive/nok-waves`: EXPERIMENTAL persistence rule evaluated per
  episode against the waves injected in the SIMULATED dimensional dataset.
- `GET /predictive/cusum`: shadow-mode CUSUM over an hourly series of that dataset.
- `GET /predictive/what-if`: HYPOTHETICAL evaluation of the Vista B mechanism.
- `GET /predictive/failure-study` (F7.b): EXPERIMENTAL failure prediction on a
  SIMULATED machine history, with baselines and per-episode evaluation.

Read-only and stateless: nothing raises a real Alert or touches measurement
history. RBAC: the analytics over the dimensional dataset and the study
results reuse `measurement.measurement_result:read` (same as the F5 quality
analytics); the process simulation reuses `live_monitor.stream` (same as
`/industrial-signals`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.edition import require_industrial_edition
from app.core.security import require_permission
from app.engines.experimental_ml import drift_cusum, nok_waves
from app.engines.experimental_ml.failure_prediction import run_study
from app.engines.process_simulation.what_if import (
    HOLD_RANGE_BAR,
    MOLD_DELTA_RANGE_C,
    what_if,
)
from app.engines.quality_analytics.synthetic import MACHINES as DIMENSIONAL_MACHINES
from app.engines.quality_analytics.synthetic import synthetic_dataset
from app.models.security import User
from app.schemas.predictive import (
    AlertEventOut,
    ContributionOut,
    CusumPointOut,
    CusumResponse,
    FailureStudyResponse,
    ModelLab,
    SweepPointOut,
    WaveEpisodeOut,
    WaveHourOut,
    WaveStudyResponse,
    WaveSummary,
    WhatIfResponse,
)
from app.services.model_lab_service import load_model_lab
from app.services.predictive_service import NOK_RATE_SERIES, cusum_study, wave_study

router = APIRouter(
    prefix="/predictive",
    tags=["predictive"],
    dependencies=[Depends(require_industrial_edition)],
)

_read_quality = require_permission("measurement.measurement_result", "read")
_read_simulation = require_permission("live_monitor", "stream")

MachineCode = Query("INY-01", pattern=r"^INY-0[12]$")


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


@router.get("/model-lab", response_model=ModelLab)
def read_model_lab(_user: User = Depends(_read_quality)) -> ModelLab:
    return load_model_lab()


@router.get("/nok-waves", response_model=WaveStudyResponse)
def read_nok_waves(
    machine: str = MachineCode,
    window: int = Query(5, ge=1, le=50),
    threshold: int = Query(4, ge=1, le=100),
    horizon: int = Query(15, ge=0, le=60),
    _user: User = Depends(_read_quality),
) -> WaveStudyResponse:
    if machine not in DIMENSIONAL_MACHINES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Machine not found.")
    study = wave_study(machine, window, threshold, horizon)
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
    return WaveStudyResponse(
        engine_name=nok_waves.ENGINE_NAME,
        engine_version=nok_waves.ENGINE_VERSION,
        machine=machine,
        window=window,
        threshold=threshold,
        horizon_groups=horizon,
        group_interval_min=minute,
        rule=(
            f"Alertar cuando los últimos {window} grupos inspeccionados suman al menos "
            f"{threshold} piezas NOK. Solo usa NOK ya medidos: puede detectar una racha "
            "iniciada, no anticipar su inicio."
        ),
        episode_definition=(
            "Episodio = oleada inyectada en el dataset sintético (verdad conocida). Se cuenta "
            f"como anticipado si hay alerta en los {horizon} grupos previos al inicio, detectado "
            "si la primera alerta cae durante la oleada, y no detectado si no hay alerta. Una "
            "alerta fuera de toda oleada es falsa alarma."
        ),
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
    _user: User = Depends(_read_quality),
) -> CusumResponse:
    variables = {v.key: v for v in synthetic_dataset().variables}
    if series != NOK_RATE_SERIES and series not in variables:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Series not found.")
    study = cusum_study(machine, series, k, h)
    label, unit = (
        ("Tasa NOK horaria", "fracción")
        if series == NOK_RATE_SERIES
        else (variables[series].name, variables[series].unit)
    )
    r = study.result
    out = CusumResponse(
        engine_name=drift_cusum.ENGINE_NAME,
        engine_version=drift_cusum.ENGINE_VERSION,
        machine=machine,
        series=series,
        series_label=f"{label} · media horaria" if series != NOK_RATE_SERIES else label,
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
