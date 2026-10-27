"""Deterministic, stateless evaluation of simulated process signals.

Design:
- A scenario's cycle timeline (one entry per injection shot: phase durations,
  peak/holding pressure, active nest, fault flags) is built once from a seeded
  RNG and cached. Same scenario + machine -> same timeline, always.
- A channel's value at time t is a pure function of (timeline, channel, t).
  Measurement noise comes from a hash of (seed, channel, sample index), not
  from RNG state, so a value never changes with the zoom window requested.
- Nothing reads or writes the database: "restoring" a scenario is a no-op by
  construction, and no user/catalog data can ever be touched.

Leakage guard: no parameter here depends on real or simulated quality labels.
`process_ok` is derived only from the simulated process window.
"""

from __future__ import annotations

import math
import random
import zlib
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

from app.engines.process_simulation.catalog import (
    MACHINES,
    MachineDefinition,
    SignalDefinition,
    get_signal,
    parse_signal_id,
)
from app.engines.process_simulation.scenarios import Scenario, ScenarioEvent, get_scenario
from app.engines.timeseries.downsample import minmax_downsample

GENERATOR_VERSION = "process-sim-1.1.0"
BASE_SEED = 20261026
SCENARIO_START = datetime(2026, 10, 20, 6, 0, tzinfo=UTC)
SCENARIO_DURATION_S = 8 * 3600.0

NEST_COUNT = 12
SHOT_STROKE_MM = 60.0
CUSHION_MM = 6.0
RETRACTED_MM = CUSHION_MM + SHOT_STROKE_MM
SPEED_RAMP_S = 0.1
RECOVERY_DELAY_S = 0.3
RECOVERY_S = 6.0
BACK_PRESSURE_BAR = 80.0
PEAK_PRESSURE_BAR = 1100.0
MOLD_TEMP_C = 55.0
BARREL_TEMP_C = 230.0
COOLING_TIME_S = 18.0

# Simulated process window behind the `process_ok` flag (not a real spec).
PEAK_WINDOW_BAR = (1000.0, 1200.0)
HOLD_WINDOW_BAR = (540.0, 680.0)
MOLD_TEMP_MAX_C = 60.0

# IQ-F4 "Vista B": synthetic dimension with an IMPOSED causal mechanism, used
# only to demonstrate correlation/regression/lag analysis on known ground
# truth. Process channels never depend on it (no leakage the other way).
INSPECTION_DELAY_S = 300.0
DIM_NOMINAL_MM = 12.0
DIM_TOL_MM = 0.05
DIM_MOLD_COEF_MM_PER_C = 0.006
DIM_HOLD_COEF_MM_PER_BAR = -0.0006
DIM_NOISE_MM = 0.007
NEST_OFFSET_SD_MM = 0.003
# Random part of the hold pressure around its setpoint (bar), cycle to cycle.
HOLD_NOISE_BAR = 4.0
HOLD_REFERENCE_BAR = 620.0
DIM_KEYS = frozenset({"dim_pins_length", "dim_nok"})

# Above this many native samples in the requested window, profile channels
# switch to a per-cycle envelope and slow channels to a coarser uniform grid.
RAW_EVAL_LIMIT = 6000

Mode = Literal["raw", "envelope"]


@dataclass(frozen=True)
class Cycle:
    index: int
    start: float
    close_s: float
    fill_s: float
    hold_s: float
    cool_s: float
    open_s: float
    peak_pressure: float
    hold_pressure: float
    fill_speed: float
    cushion: float
    cavity: int
    shot: int
    fault: bool
    alarm: bool
    process_ok: bool
    dim_length: float
    dim_nok: bool

    @property
    def fill_start(self) -> float:
        return self.close_s

    @property
    def hold_start(self) -> float:
        return self.close_s + self.fill_s

    @property
    def cool_start(self) -> float:
        return self.hold_start + self.hold_s

    @property
    def recovery_start(self) -> float:
        return self.cool_start + RECOVERY_DELAY_S

    @property
    def recovery_end(self) -> float:
        return self.recovery_start + RECOVERY_S

    @property
    def open_start(self) -> float:
        return self.cool_start + self.cool_s

    @property
    def duration(self) -> float:
        return self.open_start + self.open_s

    @property
    def end(self) -> float:
        return self.start + self.duration

    def keypoint_phases(self) -> tuple[float, ...]:
        """Phase offsets where profile waveforms have vertices (peaks, edges)."""
        eps = 1e-3
        return (
            0.0,
            self.fill_start,
            self.fill_start + SPEED_RAMP_S,
            self.hold_start - SPEED_RAMP_S,
            self.hold_start,
            self.hold_start + 0.3,
            self.cool_start - eps,
            self.cool_start,
            self.recovery_start,
            self.recovery_end - eps,
            self.recovery_end,
            self.open_start - eps,
            self.open_start,
            self.duration - eps,
        )


@dataclass(frozen=True)
class Timeline:
    scenario: Scenario
    # Deviations actually applied (the scenario for the primary machine,
    # nominal behaviour for the others).
    effective: Scenario
    machine: MachineDefinition
    seed: int
    cycles: tuple[Cycle, ...]
    starts: tuple[float, ...]

    def cycle_at(self, t: float) -> Cycle | None:
        i = bisect_right(self.starts, t) - 1
        if i >= 0 and t < self.cycles[i].end:
            return self.cycles[i]
        return None

    def last_cycle_before(self, t: float) -> Cycle | None:
        i = bisect_right(self.starts, t) - 1
        return self.cycles[i] if i >= 0 else None


@dataclass(frozen=True)
class SeriesResult:
    signal_id: str
    signal: SignalDefinition
    machine: MachineDefinition
    # (offset seconds from SCENARIO_START, value)
    points: list[tuple[float, float]]
    native_points: int
    downsampled: bool
    mode: Mode


# --- deterministic noise ----------------------------------------------------

_MASK64 = (1 << 64) - 1


def _splitmix64(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & _MASK64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & _MASK64
    return x ^ (x >> 31)


def _unit(seed: int, stream: int, index: int, k: int) -> float:
    h = _splitmix64(seed ^ _splitmix64(stream ^ _splitmix64(index * 4 + k)))
    return (h >> 11) / float(1 << 53)


def _noise(seed: int, stream: int, index: int) -> float:
    """Approximately standard-normal value, a pure function of its inputs."""
    total = sum(_unit(seed, stream, index, k) for k in range(4))
    return (total - 2.0) * math.sqrt(3.0)


def _stream(key: str) -> int:
    return zlib.crc32(key.encode("utf-8"))


# --- scenario helpers ---------------------------------------------------------


def _piecewise(points: tuple[tuple[float, float], ...], t: float) -> float:
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:], strict=False):
        if t0 <= t < t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return points[-1][1]


def _step(points: tuple[tuple[float, float], ...], t: float) -> float:
    value = points[0][1]
    for offset, v in points:
        if offset <= t:
            value = v
    return value


def _window_containing(windows: tuple[tuple[float, float], ...], t: float) -> tuple[float, float] | None:
    for start, duration in windows:
        if start <= t < start + duration:
            return start, duration
    return None


# --- timeline -----------------------------------------------------------------


def _machine(code: str) -> MachineDefinition:
    for machine in MACHINES:
        if machine.code == code:
            return machine
    raise KeyError(code)


def nest_offsets(machine_code: str) -> tuple[float, ...]:
    """Fixed per-nest offset of the Vista B dimension (mm), nests 1..NEST_COUNT."""
    nest_rng = random.Random(f"{BASE_SEED}:nests:{_machine(machine_code).code}")
    return tuple(nest_rng.gauss(0.0, NEST_OFFSET_SD_MM) for _ in range(NEST_COUNT))


@lru_cache(maxsize=32)
def build_timeline(scenario_id: str, machine_code: str) -> Timeline:
    """Cycle-by-cycle timeline for one scenario and machine (cached, deterministic)."""
    scenario = get_scenario(scenario_id)
    machine = _machine(machine_code)
    effective = scenario if machine.primary else get_scenario("normal")
    rng = random.Random(f"{BASE_SEED}:{scenario.id}:{machine.code}")
    # Separate streams so the synthetic quality layer never perturbs process values.
    rng_quality = random.Random(f"{BASE_SEED}:{scenario.id}:{machine.code}:quality")
    offsets = nest_offsets(machine.code)
    seed = _splitmix64(BASE_SEED ^ zlib.crc32(f"{scenario.id}:{machine.code}".encode()))

    cycles: list[Cycle] = []
    t = 0.0
    shot = 48_000 if machine.primary else 69_000
    while True:
        downtime = _window_containing(effective.downtimes, t)
        if downtime is not None:
            t = downtime[0] + downtime[1]
            continue

        close_s = 2.0 + abs(rng.gauss(0.0, 0.04))
        fill_s = 1.2 + rng.gauss(0.0, 0.015)
        hold_s = 5.0
        cool_s = COOLING_TIME_S
        open_s = 3.0 + abs(rng.gauss(0.0, 0.05))
        duration = close_s + fill_s + hold_s + cool_s + open_s
        if t + duration > SCENARIO_DURATION_S:
            break

        mold_delta = _piecewise(effective.mold_temp_delta, t)
        spread = _step(effective.peak_spread, t)
        # Hotter mold -> lower melt viscosity -> slightly lower peak pressure.
        peak = PEAK_PRESSURE_BAR - 6.0 * mold_delta + rng.gauss(0.0, 12.0 * spread)
        spiked = any(t <= s < t + duration for s in effective.pressure_spikes)
        if spiked:
            # A scripted spike must leave the process window whatever the random spread.
            peak = max(peak * 1.14, PEAK_WINDOW_BAR[1] * 1.03)
        hold_pressure = _step(effective.hold_setpoints, t) + rng.gauss(0.0, HOLD_NOISE_BAR)
        fault = _window_containing(effective.fault_windows, t) is not None
        cushion = CUSHION_MM + rng.gauss(0.0, 0.08)
        process_ok = (
            PEAK_WINDOW_BAR[0] <= peak <= PEAK_WINDOW_BAR[1]
            and HOLD_WINDOW_BAR[0] <= hold_pressure <= HOLD_WINDOW_BAR[1]
            and MOLD_TEMP_C + mold_delta <= MOLD_TEMP_MAX_C
            and not fault
        )
        cavity = shot % NEST_COUNT + 1
        nest_offset = offsets[cavity - 1]
        worn = effective.worn_nest
        if worn is not None and cavity == worn[0] and t < worn[2]:
            nest_offset += worn[1]
        dim_length = (
            DIM_NOMINAL_MM
            + DIM_MOLD_COEF_MM_PER_C * mold_delta
            + DIM_HOLD_COEF_MM_PER_BAR * (hold_pressure - HOLD_REFERENCE_BAR)
            + nest_offset
            + rng_quality.gauss(0.0, DIM_NOISE_MM)
        )
        cycles.append(
            Cycle(
                index=len(cycles),
                start=t,
                close_s=close_s,
                fill_s=fill_s,
                hold_s=hold_s,
                cool_s=cool_s,
                open_s=open_s,
                peak_pressure=peak,
                hold_pressure=hold_pressure,
                fill_speed=SHOT_STROKE_MM / (fill_s - SPEED_RAMP_S),
                cushion=cushion,
                cavity=cavity,
                shot=shot,
                fault=fault,
                alarm=fault or spiked,
                process_ok=process_ok,
                dim_length=dim_length,
                dim_nok=abs(dim_length - DIM_NOMINAL_MM) > DIM_TOL_MM,
            )
        )
        shot += 1
        t += duration

    return Timeline(
        scenario=scenario,
        effective=effective,
        machine=machine,
        seed=seed,
        cycles=tuple(cycles),
        starts=tuple(c.start for c in cycles),
    )


# --- channel models -------------------------------------------------------------


def _per_cycle_value(key: str, c: Cycle) -> float:
    if key == "holding_pressure":
        return c.hold_pressure
    if key == "cooling_time":
        return c.cool_s
    if key == "cycle_time":
        return c.duration
    if key == "active_cavity":
        return float(c.cavity)
    if key == "shot_counter":
        return float(c.shot)
    if key == "process_ok":
        return 1.0 if c.process_ok else 0.0
    if key == "dim_pins_length":
        return c.dim_length
    if key == "dim_nok":
        return 1.0 if c.dim_nok else 0.0
    raise KeyError(key)


def report_time(key: str, c: Cycle) -> float:
    """When a per-cycle value becomes available: at cycle start, or after inspection."""
    return c.start + (INSPECTION_DELAY_S if key in DIM_KEYS else 0.0)


def _injection_pressure(c: Cycle | None, p: float, n: float) -> float:
    if c is None:
        return max(0.0, 2.0 + n)
    if p < c.fill_start:
        v = 5.0
    elif p < c.hold_start:
        frac = (p - c.fill_start) / c.fill_s
        v = 40.0 + (c.peak_pressure - 40.0) * frac**1.6
    elif p < c.cool_start:
        q = p - c.hold_start
        v = c.hold_pressure + (c.peak_pressure - c.hold_pressure) * math.exp(-q / 0.08)
    elif c.recovery_start <= p < c.recovery_end:
        v = BACK_PRESSURE_BAR
    else:
        v = 5.0
    return max(0.0, v + 3.0 * n)


def _screw_position(c: Cycle | None, p: float, n: float) -> float:
    if c is None:
        return RETRACTED_MM + 0.05 * n
    held = c.cushion - 0.6
    if p < c.fill_start:
        pos = RETRACTED_MM
    elif p < c.hold_start:
        frac = (p - c.fill_start) / c.fill_s
        pos = RETRACTED_MM - (RETRACTED_MM - c.cushion) * (1.0 - (1.0 - frac) ** 1.8)
    elif p < c.cool_start:
        pos = c.cushion - 0.6 * (p - c.hold_start) / c.hold_s
    elif p < c.recovery_start:
        pos = held
    elif p < c.recovery_end:
        pos = held + (RETRACTED_MM - held) * (p - c.recovery_start) / RECOVERY_S
    else:
        pos = RETRACTED_MM
    return pos + 0.05 * n


def _injection_speed(c: Cycle | None, p: float, n: float) -> float:
    if c is None or not (c.fill_start <= p < c.hold_start):
        return 0.0
    ramp = min(1.0, (p - c.fill_start) / SPEED_RAMP_S, (c.hold_start - p) / SPEED_RAMP_S)
    return max(0.0, c.fill_speed * ramp + 0.4 * n)


def _motor_current(c: Cycle | None, p: float, n: float) -> float:
    if c is None:
        return 6.0 + 0.3 * n
    if p < c.fill_start or p >= c.open_start:
        base = 14.0
    elif p < c.hold_start:
        base = 30.0
    elif p < c.cool_start:
        base = 20.0
    elif c.recovery_start <= p < c.recovery_end:
        base = 36.0
    else:
        base = 11.0
    if c.fault:
        base = base * 1.3 + 4.0
    return base + 0.6 * n


def _cycle_active(c: Cycle | None, p: float) -> float:
    return 1.0 if c is not None and c.fill_start <= p < c.open_start else 0.0


def evaluate(timeline: Timeline, key: str, t: float) -> float:
    """Value of channel ``key`` at offset ``t`` seconds from the scenario start."""
    signal = get_signal(key)
    if signal.sampling == "per_cycle":
        # Inspection results are only known INSPECTION_DELAY_S after the cycle.
        lookup = t - INSPECTION_DELAY_S if key in DIM_KEYS else t
        c = timeline.last_cycle_before(lookup) or timeline.cycles[0]
        return _per_cycle_value(key, c)

    rate = signal.rate_hz or 1.0
    n = _noise(timeline.seed, _stream(key), math.floor(t * rate))
    sc = timeline.effective
    c = timeline.cycle_at(t)
    p = t - c.start if c is not None else 0.0

    if key == "injection_pressure":
        return _injection_pressure(c, p, n)
    if key == "screw_position":
        return _screw_position(c, p, n)
    if key == "injection_speed":
        return _injection_speed(c, p, n)
    if key == "motor_current":
        return _motor_current(c, p, n)
    if key == "cycle_active":
        return _cycle_active(c, p)
    if key == "barrel_temp":
        return BARREL_TEMP_C + 0.6 * math.sin(2 * math.pi * t / 420.0) + 0.15 * n
    if key == "mold_temp":
        v = MOLD_TEMP_C + _piecewise(sc.mold_temp_delta, t)
        if c is not None and p >= c.hold_start:
            v += 0.6 * math.exp(-(p - c.hold_start) / 6.0)
        downtime = _window_containing(sc.downtimes, t)
        if downtime is not None:
            v -= 3.0 * (1.0 - math.exp(-(t - downtime[0]) / 900.0))
        return v + 0.08 * n
    if key == "vibration":
        if c is None:
            return abs(0.3 + 0.05 * n)
        v = 2.1 + 0.25 * math.sin(2 * math.pi * t / 97.0)
        if c.fault:
            v += 1.8
        return abs(v + 0.12 * n)
    if key == "auto_mode":
        return 0.0 if _window_containing(sc.downtimes, t) is not None else 1.0
    if key == "alarm":
        if _window_containing(sc.alarm_windows, t) is not None:
            return 1.0
        return 1.0 if c is not None and c.alarm else 0.0
    if key == "ambient_humidity":
        return (
            46.0
            + 4.0 * math.sin(2 * math.pi * t / 19080.0)
            + 1.5 * math.sin(2 * math.pi * t / 1700.0 + 1.0)
            + 0.3 * n
        )
    if key == "aux_voltage":
        return 24.0 + 0.04 * n
    raise KeyError(key)


# --- series ---------------------------------------------------------------------


def _window_edges(sc: Scenario, start: float, end: float) -> list[float]:
    edges: list[float] = []
    for w_start, duration in (*sc.alarm_windows, *sc.fault_windows, *sc.downtimes):
        for edge in (w_start, w_start + duration):
            for t in (edge - 1e-3, edge):
                if start <= t <= end:
                    edges.append(t)
    return edges


def _uniform_grid(start: float, end: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step = (end - start) / (count - 1)
    return [start + i * step for i in range(count)]


def _native_grid(start: float, end: float, rate: float) -> list[float]:
    # Aligned to absolute multiples of 1/rate so the same instant always maps
    # to the same sample (and the same noise) whatever window is requested.
    first = math.ceil(start * rate)
    last = math.floor(end * rate)
    return [k / rate for k in range(first, last + 1)]


def generate_series(
    scenario_id: str, signal_id: str, start_s: float, end_s: float, max_points: int
) -> SeriesResult:
    """Points of one channel over ``[start_s, end_s]`` (offsets), at most ``max_points``.

    Raises:
        KeyError: unknown scenario or signal id.
        ValueError: empty/invalid window or ``max_points`` < 2.
    """
    if not (0.0 <= start_s < end_s <= SCENARIO_DURATION_S):
        raise ValueError("invalid window")
    if max_points < 2:
        raise ValueError("max_points must be >= 2")
    machine, signal = parse_signal_id(signal_id)
    timeline = build_timeline(scenario_id, machine.code)
    key = signal.key

    in_window = [c for c in timeline.cycles if c.end > start_s and c.start < end_s]
    mode: Mode = "raw"

    if signal.sampling == "per_cycle":
        points = [
            (report_time(key, c), _per_cycle_value(key, c))
            for c in timeline.cycles
            if start_s <= report_time(key, c) <= end_s
        ]
        if not points or points[0][0] > start_s:
            points.insert(0, (start_s, evaluate(timeline, key, start_s)))
        native = len(points)
    else:
        rate = signal.rate_hz or 1.0
        native = int((end_s - start_s) * rate) + 1
        if signal.sampling == "profile":
            keypoints = [c.start + ph for c in in_window for ph in c.keypoint_phases()]
            if native <= RAW_EVAL_LIMIT:
                times = _native_grid(start_s, end_s, rate) + keypoints
            else:
                mode = "envelope"
                times = keypoints + _uniform_grid(start_s, end_s, max(2, max_points // 4))
        else:
            if native <= RAW_EVAL_LIMIT:
                times = _native_grid(start_s, end_s, rate)
            else:
                mode = "envelope"
                times = _uniform_grid(start_s, end_s, RAW_EVAL_LIMIT)
            times += _window_edges(timeline.effective, start_s, end_s)
        unique = sorted({t for t in times if start_s <= t <= end_s})
        points = [(t, evaluate(timeline, key, t)) for t in unique]

    reduced = minmax_downsample(points, max_points)
    return SeriesResult(
        signal_id=signal_id,
        signal=signal,
        machine=machine,
        points=reduced,
        native_points=native,
        downsampled=mode == "envelope" or len(reduced) < len(points),
        mode=mode,
    )


def scenario_events(scenario_id: str) -> tuple[ScenarioEvent, ...]:
    """Annotated events of a scenario (they occur on the primary machine)."""
    return get_scenario(scenario_id).events
