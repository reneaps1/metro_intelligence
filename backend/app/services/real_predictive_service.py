"""IQ-F12: the predictive lab (demo step 6) over the customer's REAL dataset.

Composes the experimental engines with the locally loaded REAL dataset
(`real_dataset_service`, plan decision D8). Differences with the synthetic
path (`predictive_service`) are deliberate and surfaced in every response:

- There are no inspection groups: one piece = one group of the series.
- There is no injected ground truth: wave episodes are labelled with
  hindsight (`nok_waves.retrospective_episodes`), only to evaluate the rule.
- NOK is the machine's reported verdict, either the total result or the
  pieces whose first failing station is a given one (``station:<key>``).
- Hours are plant local time (decision D9).

Read-only, shadow-mode, cached per dataset object (a reload invalidates it).
"""

from __future__ import annotations

import threading
from collections import defaultdict
from decimal import Decimal
from typing import Any, Literal

from app.engines.experimental_ml.drift_cusum import detect_cusum_drift
from app.engines.experimental_ml.group_alarms import AlarmEvaluation, evaluate_group_alarms, longest_gap
from app.engines.experimental_ml.nok_waves import (
    GroupPoint,
    evaluate_episodes,
    persistence_alerts,
    retrospective_episodes,
)
from app.engines.experimental_ml.piece_risk import RiskStudy, run_risk_study
from app.engines.quality_analytics.dataset import DimensionalDataset
from app.services.predictive_service import NOK_RATE_SERIES, CusumStudy, HourBucket, WaveStudy

TOTAL_TARGET = "total"
STATION_PREFIX = "station:"
HOUR_S = 3600.0
LINE_LABEL = "Línea completa"

_lock = threading.Lock()
_cache: dict[tuple[Any, ...], Any] = {}
_CACHE_SIZE = 32


def _cached(key: tuple[Any, ...], build: Any) -> Any:
    with _lock:
        if key in _cache:
            return _cache[key]
    value = build()
    with _lock:
        _cache[key] = value
        while len(_cache) > _CACHE_SIZE:
            _cache.pop(next(iter(_cache)))
    return value


def reset_cache() -> None:
    """Tests only."""
    with _lock:
        _cache.clear()


def validate_target(ds: DimensionalDataset, target: str) -> str:
    """``total`` or ``station:<key>`` of a station the dataset carries; ValueError otherwise."""
    if target == TOTAL_TARGET:
        return target
    if target.startswith(STATION_PREFIX) and target[len(STATION_PREFIX) :] in {s.key for s in ds.stations}:
        return target
    raise ValueError("unknown target")


def target_label(ds: DimensionalDataset, target: str) -> str:
    if target == TOTAL_TARGET:
        return "Resultado total de la máquina"
    return f"Primera estación que falla: {ds.station(target[len(STATION_PREFIX) :]).name}"


def target_flags(ds: DimensionalDataset, target: str) -> list[bool]:
    """Per-piece NOK under the target (missing verdicts count as OK)."""
    validate_target(ds, target)

    def build() -> list[bool]:
        if target == TOTAL_TARGET:
            reported = ds.reported_nok or [p is not None for p in ds.primary_fail]
            return [bool(v) for v in reported]
        key = target[len(STATION_PREFIX) :]
        return [p == key for p in ds.primary_fail]

    flags: list[bool] = _cached((id(ds), "flags", target), build)
    return flags


def _hour_start(ts: float, offset_s: int) -> float:
    local = ts + offset_s
    return local - local % HOUR_S - offset_s


# --------------------------------------------------------------------------- waves


def real_wave_study(
    ds: DimensionalDataset,
    target: str,
    window: int,
    threshold: int,
    horizon: int,
    episode_window: int,
    episode_threshold: int,
) -> WaveStudy:
    flags = target_flags(ds, target)

    def build() -> WaveStudy:
        series = tuple(GroupPoint(ts, 1, int(bad)) for ts, bad in zip(ds.timestamps, flags, strict=True))
        episodes = retrospective_episodes(list(series), episode_window, episode_threshold)
        alerts = persistence_alerts(list(series), window, threshold)
        evaluation = evaluate_episodes(alerts, episodes, horizon)
        in_wave = [False] * len(series)
        for ep in episodes:
            for i in range(ep.start, ep.end + 1):
                in_wave[i] = True
        alert_set = set(alerts)
        buckets: dict[float, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
        for i, p in enumerate(series):
            b = buckets[_hour_start(p.ts, ds.utc_offset_s)]
            b[0] += 1
            b[1] += p.nok_pieces
            b[2] |= in_wave[i]
            b[3] |= i in alert_set
        hours = [
            HourBucket(ts, pieces, nok, bool(wave), bool(alert))
            for ts, (pieces, nok, wave, alert) in sorted(buckets.items())
        ]
        interval = (series[-1].ts - series[0].ts) / (len(series) - 1) if len(series) > 1 else 0.0
        return WaveStudy(LINE_LABEL, series, episodes, alerts, evaluation, hours, interval)

    key = (id(ds), "waves", target, window, threshold, horizon, episode_window, episode_threshold)
    study: WaveStudy = _cached(key, build)
    return study


# --------------------------------------------------------------------------- CUSUM


def series_options(ds: DimensionalDataset) -> set[str]:
    return {
        NOK_RATE_SERIES,
        *(f"{STATION_PREFIX}{s.key}" for s in ds.stations),
        *(v.key for v in ds.variables),
    }


def real_hourly_series(ds: DimensionalDataset, series: str) -> tuple[list[float], list[float]]:
    """Hourly (plant time) mean of a variable, total NOK rate or one station's attributed NOK rate."""
    if series not in series_options(ds):
        raise ValueError("unknown series")
    if series == NOK_RATE_SERIES:
        values: list[float | None] = [float(v) for v in target_flags(ds, TOTAL_TARGET)]
    elif series.startswith(STATION_PREFIX):
        values = [float(v) for v in target_flags(ds, series)]
    else:
        values = ds.values[series]
    sums: dict[float, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for ts, v in zip(ds.timestamps, values, strict=True):
        if v is None:
            continue
        b = sums[_hour_start(ts, ds.utc_offset_s)]
        b[0] += v
        b[1] += 1
    hours = sorted(sums)
    return hours, [sums[h][0] / sums[h][1] for h in hours]


def real_cusum_study(ds: DimensionalDataset, series: str, k_stdevs: float, h_stdevs: float) -> CusumStudy:
    timestamps, values = real_hourly_series(ds, series)
    result = detect_cusum_drift(
        [Decimal(repr(v)) for v in values],
        k_stdevs=Decimal(repr(k_stdevs)),
        h_stdevs=Decimal(repr(h_stdevs)),
    )
    return CusumStudy(LINE_LABEL, series, timestamps, result)


# --------------------------------------------------------------------------- group alarms


def group_alarm_study(
    ds: DimensionalDataset,
    grouping: Literal["mold_cavity", "nest"],
    target: str,
    k: int,
    n: int,
    scope: Literal["all", "after_longest_gap"],
) -> tuple[AlarmEvaluation, tuple[float, float] | None, float | None]:
    if grouping == "mold_cavity" and ds.mold_cavities is None:
        raise ValueError("dataset has no mold cavities")
    flags = target_flags(ds, target)
    column = ds.mold_cavities if grouping == "mold_cavity" else ds.cavities
    gap = longest_gap(ds.timestamps)
    since = gap[1] if scope == "after_longest_gap" and gap is not None else None
    evaluation = _cached(
        (id(ds), "alarms", grouping, target, k, n, scope),
        lambda: evaluate_group_alarms(ds.timestamps, column, flags, k, n, since=since),  # type: ignore[arg-type]
    )
    return evaluation, gap, since


# --------------------------------------------------------------------------- piece risk


def piece_risk_study(ds: DimensionalDataset, target: str) -> RiskStudy:
    """Per-piece risk with the mold cavity as group and the nest as second group (cached: a few seconds)."""
    if ds.mold_cavities is None:
        raise ValueError("dataset has no mold cavities")
    flags = target_flags(ds, target)
    molds = ds.mold_cavities
    study: RiskStudy = _cached(
        (id(ds), "risk", target),
        lambda: run_risk_study(ds.timestamps, molds, ds.cavities, flags, ds.utc_offset_s),
    )
    return study
