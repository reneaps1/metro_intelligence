"""IQ-F13: the `real_calendar` scenario, built at runtime from plain inputs (plan decision D7).

Pure: piece timestamps, piece verdicts, nest count and plant UTC offset in, a
`Scenario` out. No customer dates live in code: the service
(`app/services/process_join_service.py`) feeds it the REAL dataset and caches
the result per dataset object; it is never added to the static `SCENARIOS`.

- ``start`` = first piece floored to the minute; ``duration_s`` = last piece -
  start + 60 s.
- ``downtimes`` = every gap >= 20 min between consecutive pieces, as
  (offset from start, gap length), so no simulated cycle starts while the real
  line was stopped (a cycle already running when the stop begins finishes, as
  in the static scenarios).
- ``mold_temp_delta``: hourly NOK rate in plant time (hours with >= 100
  pieces), centred 3-hour moving average over the neighbouring qualifying
  hours, then ``clamp(4.0 * (rate / p_ref - 1), -2.0, 8.0)`` °C at each hour
  midpoint, linear in between and 0 before the first / after the last point.
  ``p_ref`` = NOK rate of all pieces. The relation with quality is therefore
  IMPOSED BY CONSTRUCTION: the scenario is ``quality_driven``.
- Everything else (hold setpoint, spikes, faults) is the ``normal`` behaviour.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime

from app.engines.process_simulation.scenarios import Scenario

CALENDAR_SCENARIO_ID = "real_calendar"
CALENDAR_SCENARIO_NAME = "Calendario real (simulado)"
CALENDAR_SCENARIO_DESCRIPTION = (
    "Proceso simulado sobre el calendario de los datos reales: inicio, fin y paros (huecos ≥ 20 min) "
    "del dataset. La temperatura de molde sigue la tasa horaria de rechazo real suavizada: relación "
    "impuesta por construcción, no medida."
)

HOUR_S = 3600
DOWNTIME_GAP_S = 20 * 60.0
MIN_HOUR_PIECES = 100
# Centred moving average: the hour itself and this many hours on each side.
SMOOTHING_HALF_WIDTH_H = 1
DELTA_GAIN_C = 4.0
DELTA_MIN_C = -2.0
DELTA_MAX_C = 8.0


def _plant_hour(ts: float, utc_offset_s: int) -> int:
    """Index of the plant-time hour containing ``ts`` (hours since the epoch, local clock)."""
    return int((ts + utc_offset_s) // HOUR_S)


def hourly_nok_rates(timestamps: Sequence[float], nok: Sequence[bool], utc_offset_s: int) -> dict[int, float]:
    """NOK rate per plant-time hour index, only for hours with at least ``MIN_HOUR_PIECES`` pieces."""
    counts: dict[int, list[int]] = {}
    for ts, bad in zip(timestamps, nok, strict=True):
        entry = counts.setdefault(_plant_hour(ts, utc_offset_s), [0, 0])
        entry[0] += 1
        entry[1] += bad
    return {h: k / n for h, (n, k) in counts.items() if n >= MIN_HOUR_PIECES}


def smoothed_rates(rates: dict[int, float]) -> dict[int, float]:
    """Centred moving average over the calendar neighbours that are present (fewer at edges and stops)."""
    out: dict[int, float] = {}
    for h in rates:
        window = [
            rates[h + k] for k in range(-SMOOTHING_HALF_WIDTH_H, SMOOTHING_HALF_WIDTH_H + 1) if h + k in rates
        ]
        out[h] = math.fsum(window) / len(window)
    return out


def mold_delta(rate: float, p_ref: float) -> float:
    """Mold temperature deviation (°C) for a smoothed NOK rate relative to the reference rate."""
    return min(DELTA_MAX_C, max(DELTA_MIN_C, DELTA_GAIN_C * (rate / p_ref - 1.0)))


def build_calendar_scenario(
    timestamps: Sequence[float],
    nok: Sequence[bool],
    nest_count: int | None,
    utc_offset_s: int,
) -> Scenario:
    """The quality-driven ``real_calendar`` scenario for a set of inspected pieces.

    Args:
        timestamps: Inspection time of every piece, epoch seconds (any order).
        nok: Verdict of every piece (True = NOK), paired with ``timestamps``.
        nest_count: Nests of the line (None = the simulator default).
        utc_offset_s: Plant local time = UTC + offset; sets the hour buckets.

    Returns:
        A deterministic scenario whose offsets are relative to ``start``.

    Raises:
        ValueError: no pieces, mismatched lengths or a non-positive nest count.
    """
    if not timestamps:
        raise ValueError("at least one piece is required")
    if len(timestamps) != len(nok):
        raise ValueError("timestamps and verdicts must have the same length")
    if nest_count is not None and nest_count < 1:
        raise ValueError("nest_count must be positive")

    ordered = sorted(timestamps)
    start = math.floor(ordered[0] / 60.0) * 60.0
    duration = ordered[-1] - start + 60.0
    downtimes = tuple(
        (a - start, b - a) for a, b in zip(ordered, ordered[1:], strict=False) if b - a >= DOWNTIME_GAP_S
    )

    p_ref = sum(nok) / len(nok)
    points: list[tuple[float, float]] = []
    if p_ref > 0.0:
        smooth = smoothed_rates(hourly_nok_rates(timestamps, nok, utc_offset_s))
        for h in sorted(smooth):
            midpoint = h * HOUR_S - utc_offset_s + HOUR_S / 2
            points.append((midpoint - start, mold_delta(smooth[h], p_ref)))
    # Repeated offsets make `_piecewise` step to 0 outside the points instead
    # of holding the first/last value.
    delta = ((points[0][0], 0.0), *points, (points[-1][0], 0.0)) if points else ((0.0, 0.0),)

    return Scenario(
        id=CALENDAR_SCENARIO_ID,
        name=CALENDAR_SCENARIO_NAME,
        description=CALENDAR_SCENARIO_DESCRIPTION,
        mold_temp_delta=delta,
        downtimes=downtimes,
        start=datetime.fromtimestamp(start, tz=UTC),
        duration_s=duration,
        nest_count=nest_count,
        quality_driven=True,
    )
