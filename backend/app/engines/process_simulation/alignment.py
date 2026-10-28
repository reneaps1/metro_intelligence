"""IQ-F4: pairing two simulated channels for correlation/regression.

Two alignment modes, matching the two stories the demo has to tell:

- ``cycle``: one pair per machine cycle (x from cycle i, y from cycle i+lag).
  This is what *traceability by cycle/piece* gives you -- in the simulator it
  is perfect; in a real plant it requires PLC/MES integration.
- ``time``: x(t) paired with y(t + lag seconds) on a uniform grid. This is the
  *illustrative join by time* available without traceability; the inspection
  delay shows up as the lag that maximises |r|.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean
from typing import Literal

from app.engines.process_simulation.catalog import SignalDefinition, parse_signal_id
from app.engines.process_simulation.generator import (
    Cycle,
    Timeline,
    _per_cycle_value,
    build_timeline,
    causal_imposed,
    evaluate,
    scenario_duration,
)
from app.engines.process_simulation.scenarios import Scenario, resolve_scenario
from app.engines.statistics import LinearFit, linear_fit

AlignMode = Literal["time", "cycle"]

TIME_GRID_POINTS = 1200
SCAN_GRID_POINTS = 600
DEFAULT_TIME_LAGS_S: tuple[float, ...] = tuple(float(s) for s in range(-600, 901, 30))
DEFAULT_CYCLE_LAGS: tuple[int, ...] = tuple(range(-10, 11))
MAX_SCATTER_POINTS = 1500


@dataclass(frozen=True)
class LagScore:
    lag: float
    n: int
    pearson_r: float | None


@dataclass(frozen=True)
class CorrelationResult:
    mode: AlignMode
    lag: float
    fit: LinearFit
    # Scatter pairs, evenly thinned to at most MAX_SCATTER_POINTS.
    pairs: list[tuple[float, float]]
    scan: list[LagScore]
    best_lag: float | None
    causal_imposed: bool


def cycle_feature(timeline: Timeline, signal: SignalDefinition, c: Cycle) -> float:
    """One value per cycle: the value itself, the profile peak, or the in-cycle mean."""
    if signal.sampling == "per_cycle":
        return _per_cycle_value(signal.key, c)
    if signal.sampling == "profile":
        return max(evaluate(timeline, signal.key, c.start + ph) for ph in c.keypoint_phases())
    return fmean(evaluate(timeline, signal.key, c.start + c.duration * f) for f in (0.1, 0.3, 0.5, 0.7, 0.9))


def _grid(start_s: float, end_s: float, count: int) -> list[float]:
    step = (end_s - start_s) / (count - 1)
    return [start_s + i * step for i in range(count)]


def _thin(pairs: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(pairs) <= MAX_SCATTER_POINTS:
        return pairs
    step = len(pairs) / MAX_SCATTER_POINTS
    return [pairs[int(i * step)] for i in range(MAX_SCATTER_POINTS)]


def _best(scan: list[LagScore]) -> float | None:
    scored = [s for s in scan if s.pearson_r is not None]
    if not scored:
        return None
    return max(scored, key=lambda s: (abs(s.pearson_r or 0.0), -abs(s.lag))).lag


def correlate(
    scenario: str | Scenario,
    x_id: str,
    y_id: str,
    start_s: float,
    end_s: float,
    mode: AlignMode,
    lag: float,
    scan_lags: Sequence[float] | None = None,
) -> CorrelationResult:
    """Pair two channels, fit ``y = a + b·x`` at ``lag``, optionally scan other lags.

    Raises:
        KeyError: unknown scenario or signal.
        ValueError: invalid window, or ``cycle`` mode across different machines.
    """
    sc = resolve_scenario(scenario)
    duration = scenario_duration(sc)
    if not (0.0 <= start_s < end_s <= duration):
        raise ValueError("invalid window")
    x_machine, x_signal = parse_signal_id(x_id)
    y_machine, y_signal = parse_signal_id(y_id)
    x_timeline = build_timeline(scenario, x_machine.code)
    y_timeline = build_timeline(scenario, y_machine.code)
    causal = causal_imposed(sc, x_machine, x_signal) or causal_imposed(sc, y_machine, y_signal)

    if mode == "cycle":
        if x_machine.code != y_machine.code:
            raise ValueError("cycle alignment needs both signals from the same machine")
        cycles = x_timeline.cycles
        indices = [i for i, c in enumerate(cycles) if start_s <= c.start < end_s]
        lags = sorted({int(lag), *(int(v) for v in (scan_lags or ()))})
        y_needed = sorted({i + k for i in indices for k in lags if 0 <= i + k < len(cycles)})
        fx = {i: cycle_feature(x_timeline, x_signal, cycles[i]) for i in indices}
        fy = {j: cycle_feature(y_timeline, y_signal, cycles[j]) for j in y_needed}

        def pairs_at(k: int) -> list[tuple[float, float]]:
            return [(fx[i], fy[i + k]) for i in indices if (i + k) in fy]

        main = pairs_at(int(lag))
        scan = [
            LagScore(float(k), len(p), linear_fit([a for a, _ in p], [b for _, b in p]).pearson_r)
            for k in (int(v) for v in (scan_lags or ()))
            for p in (pairs_at(k),)
        ]
    else:

        def pairs_on(times: list[float], shift: float) -> list[tuple[float, float]]:
            return [
                (evaluate(x_timeline, x_signal.key, t), evaluate(y_timeline, y_signal.key, t + shift))
                for t in times
                if 0.0 <= t + shift <= duration
            ]

        main = pairs_on(_grid(start_s, end_s, TIME_GRID_POINTS), lag)
        scan_times = _grid(start_s, end_s, SCAN_GRID_POINTS)
        scan = []
        for shift in scan_lags or ():
            p = pairs_on(scan_times, shift)
            scan.append(
                LagScore(float(shift), len(p), linear_fit([a for a, _ in p], [b for _, b in p]).pearson_r)
            )

    fit = linear_fit([a for a, _ in main], [b for _, b in main])
    return CorrelationResult(
        mode=mode,
        lag=float(lag),
        fit=fit,
        pairs=_thin(main),
        scan=scan,
        best_lag=_best(scan) if scan else None,
        causal_imposed=causal,
    )
