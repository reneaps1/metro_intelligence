"""IQ-F7: composes the experimental engines with the synthetic dimensional
dataset (F5) for demo step 6.

- NOK waves: the synthetic dataset carries four injected waves (`WAVES`),
  which are the known ground truth the persistence rule is evaluated against.
- CUSUM: the shadow-mode `drift_cusum` engine over an hourly series of the
  same dataset (mean of one variable, or NOK rate).

Everything here is SIMULATED data and EXPERIMENTAL logic; nothing writes an
Alert/Recommendation or touches measurement history.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

from app.engines.experimental_ml.drift_cusum import DriftDetectionResult, detect_cusum_drift
from app.engines.experimental_ml.nok_waves import (
    Episode,
    GroupPoint,
    WaveEvaluation,
    evaluate_episodes,
    persistence_alerts,
)
from app.engines.quality_analytics.synthetic import MACHINES, PERIOD_START, WAVES, synthetic_dataset

HOUR_S = 3600.0
NOK_RATE_SERIES = "nok_rate"


@lru_cache(maxsize=4)
def group_series(machine: str) -> tuple[GroupPoint, ...]:
    """Inspection groups of one machine in time order, with their NOK pieces."""
    if machine not in MACHINES:
        raise ValueError("unknown machine")
    ds = synthetic_dataset()
    keys = [v.key for v in ds.variables]
    groups: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    ts: dict[int, float] = {}
    for i, m in enumerate(ds.machines):
        if m != machine:
            continue
        g = ds.group_ids[i]
        ts[g] = ds.timestamps[i]
        groups[g][0] += 1
        groups[g][1] += any(ds.nok[k][i] for k in keys)
    return tuple(
        GroupPoint(ts[g], pieces, nok)
        for g, (pieces, nok) in sorted(groups.items(), key=lambda kv: ts[kv[0]])
    )


def wave_episodes(machine: str) -> list[Episode]:
    """Known injected waves of `machine` as inclusive group-index ranges."""
    series = group_series(machine)
    start = PERIOD_START.timestamp()
    episodes: list[Episode] = []
    for offset, duration, wave_machine in WAVES:
        if wave_machine != machine:
            continue
        inside = [i for i, p in enumerate(series) if offset <= p.ts - start < offset + duration]
        if inside:
            episodes.append(Episode(inside[0], inside[-1]))
    return episodes


@dataclass(frozen=True)
class HourBucket:
    ts: float
    pieces: int
    nok_pieces: int
    in_wave: bool
    alert: bool


@dataclass(frozen=True)
class WaveStudy:
    machine: str
    series: tuple[GroupPoint, ...]
    episodes: list[Episode]
    alerts: list[int]
    evaluation: WaveEvaluation
    hours: list[HourBucket]
    group_interval_s: float


def wave_study(machine: str, window: int, threshold: int, horizon: int) -> WaveStudy:
    series = group_series(machine)
    episodes = wave_episodes(machine)
    alerts = persistence_alerts(list(series), window, threshold)
    evaluation = evaluate_episodes(alerts, episodes, horizon)
    in_wave = {i for ep in episodes for i in range(ep.start, ep.end + 1)}
    alert_set = set(alerts)
    start = PERIOD_START.timestamp()
    buckets: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for i, p in enumerate(series):
        b = buckets[int((p.ts - start) // HOUR_S)]
        b[0] += p.pieces
        b[1] += p.nok_pieces
        b[2] |= i in in_wave
        b[3] |= i in alert_set
    hours = [
        HourBucket(start + h * HOUR_S, pieces, nok, bool(wave), bool(alert))
        for h, (pieces, nok, wave, alert) in sorted(buckets.items())
    ]
    interval = (series[-1].ts - series[0].ts) / (len(series) - 1) if len(series) > 1 else 0.0
    return WaveStudy(machine, series, episodes, alerts, evaluation, hours, interval)


@dataclass(frozen=True)
class CusumStudy:
    machine: str
    series: str
    timestamps: list[float]
    result: DriftDetectionResult | None


def hourly_series(machine: str, series: str) -> tuple[list[float], list[float]]:
    """Hourly mean of one variable (or hourly NOK rate) of one machine."""
    ds = synthetic_dataset()
    keys = [v.key for v in ds.variables]
    if machine not in MACHINES:
        raise ValueError("unknown machine")
    if series != NOK_RATE_SERIES and series not in keys:
        raise ValueError("unknown series")
    start = PERIOD_START.timestamp()
    sums: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for i, m in enumerate(ds.machines):
        if m != machine:
            continue
        if series == NOK_RATE_SERIES:
            value: float | None = float(any(ds.nok[k][i] for k in keys))
        else:
            value = ds.values[series][i]
        if value is None:
            continue
        b = sums[int((ds.timestamps[i] - start) // HOUR_S)]
        b[0] += value
        b[1] += 1
    hours = sorted(sums)
    return [start + h * HOUR_S for h in hours], [sums[h][0] / sums[h][1] for h in hours]


def cusum_study(machine: str, series: str, k_stdevs: float, h_stdevs: float) -> CusumStudy:
    timestamps, values = hourly_series(machine, series)
    result = detect_cusum_drift(
        [Decimal(repr(v)) for v in values],
        k_stdevs=Decimal(repr(k_stdevs)),
        h_stdevs=Decimal(repr(h_stdevs)),
    )
    return CusumStudy(machine, series, timestamps, result)
