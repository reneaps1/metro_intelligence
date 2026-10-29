"""IQ-F13 "Vista A": REAL dimensional pieces joined by time with the SIMULATED
process of the `real_calendar` scenario (`docs/design/process-quality-join.md`).

- The calendar scenario is built from the REAL dataset (piece times, total
  verdict, number of nests, plant UTC offset) by
  `calendar_scenario.build_calendar_scenario` and cached per dataset object,
  like the other REAL services (a reload of the dataset invalidates it). It is
  never added to the static scenario list.
- The primary machine (INY-01) carries the scenario. A signal's per-cycle
  value is the same one-value-per-cycle feature as the Vista B cycle
  alignment (`alignment.cycle_feature`), computed once per signal; piece
  counts per (target, bucket) and cycle sums per (signal, bucket) are cached
  as well, so other lags, targets and bucket sizes are dictionary lookups.
- The mold temperature of this scenario follows the real reject rate (plan
  decision D7): its relation with quality is imposed by construction and the
  response says so. The other offered signals are controls.

Read-only; assumes a single worker process (same as `real_dataset_service`).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from app.engines.process_simulation.alignment import cycle_feature
from app.engines.process_simulation.calendar_scenario import build_calendar_scenario
from app.engines.process_simulation.catalog import (
    MACHINES,
    MachineDefinition,
    SignalDefinition,
    parse_signal_id,
)
from app.engines.process_simulation.generator import (
    Timeline,
    build_timeline,
    causal_imposed,
    scenario_start,
)
from app.engines.process_simulation.scenarios import Scenario
from app.engines.quality_analytics.dataset import DimensionalDataset
from app.engines.quality_analytics.process_join import (
    JoinLagScore,
    TimeJoin,
    best_lag,
    cycle_sums,
    join_at_lag,
    lag_scan,
    piece_counts,
)
from app.services.real_predictive_service import TOTAL_TARGET, target_flags, validate_target

# Process signals offered by the join (all with one value per cycle). The
# Vista B synthetic quality channels, counters and machine states are not.
JOIN_SIGNAL_KEYS = ("mold_temp", "holding_pressure", "injection_pressure", "cycle_time")
BUCKET_MINUTES = (15, 30, 60)
DEFAULT_BUCKET_MINUTES = 30
MAX_LAG_MINUTES = 180
PRIMARY_MACHINE = next(m for m in MACHINES if m.primary)

ILLUSTRATIVE_NOTE = (
    "Unión ilustrativa por tiempo: piezas dimensionales REALES agrupadas por tramos de hora de planta "
    "junto a señales de proceso SIMULADAS generadas sobre el mismo calendario. No hay trazabilidad "
    "ciclo/pieza entre ambas fuentes y nada de esto es una medición de planta."
)
CAUSAL_NOTE = (
    "La temperatura de molde simulada se construyó siguiendo la tasa de rechazo real: la relación está "
    "impuesta por construcción, no medida."
)
CONTROL_NOTE = "Señal simulada sin vínculo con la calidad: sirve de control (se espera r cercano a 0)."


@dataclass
class _Calendar:
    dataset: DimensionalDataset
    scenario: Scenario
    timeline: Timeline
    # Absolute start of every simulated cycle (UTC epoch seconds).
    starts: list[float]
    values: dict[str, list[float]] = field(default_factory=dict)
    cycles: dict[tuple[str, int], dict[int, tuple[float, int]]] = field(default_factory=dict)
    pieces: dict[tuple[str, int], dict[int, tuple[int, int]]] = field(default_factory=dict)


@dataclass(frozen=True)
class ProcessJoin:
    scenario: Scenario
    signal: SignalDefinition
    signal_name: str
    join: TimeJoin
    # (lag in minutes, score), ascending lags.
    scan: list[tuple[int, JoinLagScore]]
    best_lag_minutes: int | None
    causal_imposed: bool
    notes: list[str]


_lock = threading.Lock()
_current: _Calendar | None = None


def reset_cache() -> None:
    """Tests only."""
    global _current
    with _lock:
        _current = None


def _calendar(ds: DimensionalDataset) -> _Calendar:
    """The cached calendar of ``ds``; rebuilt when the dataset object changes. Call under ``_lock``."""
    global _current
    if _current is None or _current.dataset is not ds:
        nests = len(ds.distinct(ds.cavities)) or None
        scenario = build_calendar_scenario(
            ds.timestamps, target_flags(ds, TOTAL_TARGET), nests, ds.utc_offset_s
        )
        timeline = build_timeline(scenario, PRIMARY_MACHINE.code)
        origin = scenario_start(scenario).timestamp()
        _current = _Calendar(ds, scenario, timeline, [origin + c.start for c in timeline.cycles])
    return _current


def calendar_scenario(ds: DimensionalDataset) -> Scenario:
    """The `real_calendar` scenario of a dataset (cached per dataset object)."""
    with _lock:
        return _calendar(ds).scenario


def join_signal(signal_id: str) -> tuple[MachineDefinition, SignalDefinition]:
    """Resolve a signal offered by the join (primary machine only).

    Raises:
        ValueError: unknown signal id, another machine or a signal the join does not offer.
    """
    try:
        machine, signal = parse_signal_id(signal_id)
    except KeyError:
        raise ValueError("unknown signal") from None
    if machine.code != PRIMARY_MACHINE.code or signal.key not in JOIN_SIGNAL_KEYS:
        raise ValueError("signal not offered by the join")
    return machine, signal


def signal_label(signal: SignalDefinition) -> str:
    """Name of the per-cycle value: the profile peak or the in-cycle mean for non per-cycle channels."""
    if signal.sampling == "profile":
        return f"{signal.name} (pico por ciclo)"
    if signal.sampling == "continuous":
        return f"{signal.name} (media por ciclo)"
    return signal.name


def validate_window(bucket_minutes: int, lag_minutes: int) -> None:
    """Raises ValueError unless the bucket is offered and the lag is whole buckets within ±180 min."""
    if bucket_minutes not in BUCKET_MINUTES:
        raise ValueError("unsupported bucket")
    if abs(lag_minutes) > MAX_LAG_MINUTES or lag_minutes % bucket_minutes:
        raise ValueError("invalid lag")


def process_join(
    ds: DimensionalDataset, signal_id: str, target: str, bucket_minutes: int, lag_minutes: int
) -> ProcessJoin:
    """Join the pieces of ``ds`` under ``target`` with a simulated signal of the calendar scenario.

    Raises:
        ValueError: signal, target, bucket or lag not valid (see the validators above).
    """
    machine, signal = join_signal(signal_id)
    validate_target(ds, target)
    validate_window(bucket_minutes, lag_minutes)
    bucket_s = bucket_minutes * 60
    offset = ds.utc_offset_s

    with _lock:
        cal = _calendar(ds)
        values = cal.values.get(signal.key)
        if values is None:
            values = [cycle_feature(cal.timeline, signal, c) for c in cal.timeline.cycles]
            cal.values[signal.key] = values
        cycles = cal.cycles.get((signal.key, bucket_s))
        if cycles is None:
            cycles = cycle_sums(cal.starts, values, bucket_s, offset)
            cal.cycles[(signal.key, bucket_s)] = cycles
        pieces = cal.pieces.get((target, bucket_s))
        if pieces is None:
            pieces = piece_counts(ds.timestamps, target_flags(ds, target), bucket_s, offset)
            cal.pieces[(target, bucket_s)] = pieces
        scenario = cal.scenario

    steps = MAX_LAG_MINUTES // bucket_minutes
    scan = lag_scan(pieces, cycles, range(-steps, steps + 1), bucket_s, offset)
    best = best_lag(scan)
    causal = causal_imposed(scenario, machine, signal)
    return ProcessJoin(
        scenario=scenario,
        signal=signal,
        signal_name=signal_label(signal),
        join=join_at_lag(pieces, cycles, lag_minutes // bucket_minutes, bucket_s, offset),
        scan=[(s.lag_buckets * bucket_minutes, s) for s in scan],
        best_lag_minutes=None if best is None else best * bucket_minutes,
        causal_imposed=causal,
        notes=[ILLUSTRATIVE_NOTE, CAUSAL_NOTE if causal else CONTROL_NOTE],
    )
