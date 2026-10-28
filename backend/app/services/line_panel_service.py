"""IQ-F14: line quality panel -- line sequence, rule replay, moments and replay windows.

Composes the `line_alarms` engine with a `DimensionalDataset`
(`docs/design/line-quality-panel.md`):

- The *line sequence* is every piece of the dataset (or of one machine, when the
  dataset carries machines: the synthetic one interleaves two) in line order --
  timestamp, then dataset order. The piece verdict is `piece_nok_flags` with
  every variable and no station filter: the machine's reported verdict on REAL
  data, the specification on synthetic data. A missing verdict counts as OK.
- The engine runs ONCE over the whole sequence; the result is cached per
  dataset object and machine (a reload of the REAL dataset invalidates it).
  `p_ref` is the NOK rate of that whole sequence.
- *Moments* are the presenter's jump targets (longest streaks, strongest
  attention alarms, longest calm stretches).
- A *replay window* slices the cached columns: up to `LEAD_MAX` lead pieces
  before the window so strips and rule windows are full, indices relative to
  the first returned piece, 8 h plant-time shifts from 06:00 and the counts of
  the current shift before the first returned piece.

Read-only and shadow-mode: nothing is persisted, nothing acts on production.
"""

from __future__ import annotations

import threading
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Literal

from app.engines.line_alarms.rules import LineAlarm, LineEvaluation, Rule, evaluate_line
from app.engines.quality_analytics.analytics import QualityFilter, piece_nok_flags
from app.engines.quality_analytics.dataset import DimensionalDataset

Provenance = Literal["REAL", "SIMULATED"]
MomentKind = Literal["stop", "attention", "normal"]

LEAD_MAX = 600
HOUR_S = 3600
SHIFT_S = 8 * HOUR_S
SHIFT_START_S = 6 * HOUR_S  # shifts start at 06:00, 14:00 and 22:00 plant time
MAX_STOPS = 8
MAX_ATTENTION = 6
MAX_NORMAL = 4
# Minimum calm stretch, and pieces replayed before an event, per provenance.
NORMAL_MIN_PIECES: dict[Provenance, int] = {"REAL": 600, "SIMULATED": 120}
EVENT_LEAD_PIECES: dict[Provenance, int] = {"REAL": 150, "SIMULATED": 36}


class UnknownMachineError(ValueError):
    """The dataset carries machines and the requested one is not among them."""


class StartOutsideDataError(ValueError):
    """The replay start is before the first or after the last piece of the line."""


@dataclass(frozen=True)
class LineSequence:
    machine: str | None
    timestamps: list[float]
    nests: list[int | None]
    mold_cavities: list[int | None] | None
    nok: list[bool]
    stations: list[str | None]  # first failing station per piece


@dataclass(frozen=True)
class Moment:
    key: str
    kind: MomentKind
    rule: Rule | None
    key_group: int | None
    raised_ts: float
    peak: float
    label: str
    replay_start_ts: float


@dataclass(frozen=True)
class LinePanel:
    dataset: DimensionalDataset
    provenance: Provenance
    line: LineSequence
    evaluation: LineEvaluation
    moments: list[Moment]


@dataclass(frozen=True)
class Shift:
    label: str
    start_ts: float
    end_ts: float


@dataclass(frozen=True)
class Baseline:
    pieces: int
    nok: int
    by_nest: list[tuple[int, int, int]]
    by_cavity: list[tuple[int, int, int]]
    by_station: list[tuple[str, int]]
    hours: list[tuple[float, int, int]]


@dataclass(frozen=True)
class Replay:
    start_ts: float
    end_ts: float
    lead: int
    shifts: list[Shift]
    baseline: Baseline
    # Per-piece columns; index 0 = first lead piece, `t` relative to `start_ts`.
    t: list[float]
    nest: list[int | None]
    cavity: list[int | None]
    nok: list[int]  # 1 = NOK, 0 = OK
    station: list[int]  # index into the dataset's stations, -1 = none
    run: list[int]
    rate: list[float | None]
    nest_ratio: list[float | None]
    nest_ratio_nest: list[int | None]
    cavity_rate: list[float | None]
    cavity_worst: list[int | None]
    # (stable id, event with indices relative to the first returned piece)
    alarms: list[tuple[str, LineAlarm]]


# --------------------------------------------------------------------------- line + cache

_lock = threading.Lock()
_cache: dict[tuple[str, int, str | None], LinePanel] = {}
_CACHE_SIZE = 8


def reset_cache() -> None:
    """Tests only."""
    with _lock:
        _cache.clear()


def provenance(ds: DimensionalDataset) -> Provenance:
    return "REAL" if ds.source_type == "REAL" else "SIMULATED"


def resolve_machine(ds: DimensionalDataset, machine: str | None) -> str | None:
    """The machine to filter on: None when the dataset has no machines, else the requested or the first."""
    machines: list[str] = ds.distinct(ds.machines)
    if not machines:
        return None
    if machine is None:
        return machines[0]
    if machine not in machines:
        raise UnknownMachineError(machine)
    return machine


def build_sequence(ds: DimensionalDataset, machine: str | None) -> LineSequence:
    rows = list(range(len(ds))) if machine is None else [i for i, m in enumerate(ds.machines) if m == machine]
    rows.sort(key=ds.timestamps.__getitem__)  # stable: timestamp, then dataset order
    flags = piece_nok_flags(ds, QualityFilter(), rows, [v.key for v in ds.variables])
    molds = ds.mold_cavities
    has_molds = molds is not None and any(c is not None for c in molds)
    return LineSequence(
        machine=machine,
        timestamps=[ds.timestamps[i] for i in rows],
        nests=[ds.cavities[i] for i in rows],
        mold_cavities=[molds[i] for i in rows] if molds is not None and has_molds else None,
        nok=[bool(f) for f in flags],
        stations=[ds.primary_fail[i] for i in rows],
    )


def line_panel(ds: DimensionalDataset, machine: str | None = None) -> LinePanel:
    """Rule replay over the whole line sequence of a dataset (cached; built once under a lock)."""
    machine = resolve_machine(ds, machine)
    key = (ds.id, id(ds), machine)
    with _lock:
        hit = _cache.get(key)
        if hit is not None and hit.dataset is ds:
            return hit
        line = build_sequence(ds, machine)
        evaluation = evaluate_line(line.timestamps, line.nests, line.mold_cavities, line.nok, line.stations)
        prov = provenance(ds)
        panel = LinePanel(ds, prov, line, evaluation, find_moments(prov, line.timestamps, evaluation))
        _cache[key] = panel
        while len(_cache) > _CACHE_SIZE:
            _cache.pop(next(iter(_cache)))
        return panel


# --------------------------------------------------------------------------- moments


def _attention_label(a: LineAlarm, rate_window: int) -> str:
    if a.rule == "R2":
        return f"Nido {a.key} fuera de patrón: {a.peak:.{0 if a.peak >= 10 else 1}f}× el resto"
    return f"Tasa NOK alta: {a.peak * 100:.1f} % en {rate_window} piezas (límite {a.limit * 100:.1f} %)"


def calm_stretches(n: int, alarms: list[LineAlarm]) -> list[tuple[int, int]]:
    """Maximal [start, stop) index ranges with no priority 1/2 alarm active."""
    delta = [0] * (n + 1)
    for a in alarms:
        if a.priority <= 2:
            delta[a.raised_index] += 1
            delta[n if a.cleared_index is None else a.cleared_index] -= 1
    out: list[tuple[int, int]] = []
    active = 0
    start: int | None = None
    for i in range(n):
        active += delta[i]
        if active == 0 and start is None:
            start = i
        elif active > 0 and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, n))
    return out


def find_moments(prov: Provenance, ts: list[float], ev: LineEvaluation) -> list[Moment]:
    """Presenter jump targets: stops (longest streak first), attention (strongest first), normal."""
    if not ts:
        return []
    lead = EVENT_LEAD_PIECES[prov]

    def before(a: LineAlarm) -> float:
        return ts[max(0, a.raised_index - lead)]

    stops = sorted((a for a in ev.alarms if a.rule == "R1"), key=lambda a: (-a.peak, a.raised_index))
    # R2 (ratio) and R3 (rate) peaks are compared as multiples of their own limit.
    attention = sorted(
        (a for a in ev.alarms if a.rule in ("R2", "R3")),
        key=lambda a: (-(a.peak / a.limit if a.limit > 0 else a.peak), a.raised_index),
    )
    calm = [s for s in calm_stretches(len(ts), ev.alarms) if s[1] - s[0] >= NORMAL_MIN_PIECES[prov]]
    calm.sort(key=lambda s: (s[0] - s[1], s[0]))
    moments = [
        Moment(
            f"stop-{rank}",
            "stop",
            "R1",
            None,
            a.raised_ts,
            a.peak,
            f"Racha de {int(a.peak)} NOK consecutivas",
            before(a),
        )
        for rank, a in enumerate(stops[:MAX_STOPS], start=1)
    ]
    moments += [
        Moment(
            f"attention-{rank}",
            "attention",
            a.rule,
            a.key if a.rule == "R2" else None,
            a.raised_ts,
            a.peak,
            _attention_label(a, ev.config.rate_window),
            before(a),
        )
        for rank, a in enumerate(attention[:MAX_ATTENTION], start=1)
    ]
    moments += [
        Moment(
            f"normal-{rank}",
            "normal",
            None,
            None,
            ts[start],
            float(stop - start),
            f"Operación normal: {stop - start} piezas sin alarmas de paro ni de atención",
            ts[start + (stop - start) // 10],
        )
        for rank, (start, stop) in enumerate(calm[:MAX_NORMAL], start=1)
    ]
    return moments


# --------------------------------------------------------------------------- replay windows


def shift_start(ts: float, utc_offset_s: int) -> float:
    """Start (epoch) of the 8 h plant-time shift containing ``ts`` (06:00, 14:00, 22:00)."""
    local = ts + utc_offset_s
    return local - (local - SHIFT_START_S) % SHIFT_S - utc_offset_s


def shift_label(start: float, utc_offset_s: int) -> str:
    hour = int((start + utc_offset_s) % 86_400) // HOUR_S
    return f"{hour:02d}:00–{(hour + 8) % 24:02d}:00"


def _hour_start(ts: float, utc_offset_s: int) -> float:
    local = ts + utc_offset_s
    return local - local % HOUR_S - utc_offset_s


def _baseline(panel: LinePanel, first: int) -> Baseline:
    """Counts of the shift containing piece ``first``, from the shift start up to (not incl.) it."""
    line, ds = panel.line, panel.dataset
    ts = line.timestamps
    begin = bisect_left(ts, shift_start(ts[first], ds.utc_offset_s), 0, first)
    nests: dict[int, list[int]] = {g: [0, 0] for g in ds.distinct(line.nests)}
    molds = line.mold_cavities
    cavities: dict[int, list[int]] = {g: [0, 0] for g in ds.distinct(molds)} if molds is not None else {}
    stations: dict[str, int] = {s.key: 0 for s in ds.stations}
    hours: dict[float, list[int]] = defaultdict(lambda: [0, 0])
    nok_total = 0
    for i in range(begin, first):
        bad = line.nok[i]
        nok_total += bad
        nest = line.nests[i]
        if nest is not None:
            nests[nest][0] += 1
            nests[nest][1] += bad
        mold = None if molds is None else molds[i]
        if mold is not None:
            cavities[mold][0] += 1
            cavities[mold][1] += bad
        station = line.stations[i]
        if bad and station is not None:
            stations[station] += 1
        hour = hours[_hour_start(ts[i], ds.utc_offset_s)]
        hour[0] += 1
        hour[1] += bad
    return Baseline(
        pieces=first - begin,
        nok=nok_total,
        by_nest=[(g, n, k) for g, (n, k) in nests.items()],
        by_cavity=[(g, n, k) for g, (n, k) in cavities.items()],
        by_station=list(stations.items()),
        hours=[(h, n, k) for h, (n, k) in sorted(hours.items())],
    )


def alarm_id(a: LineAlarm) -> str:
    """Stable id from the absolute raise index: ``R1::1234``, ``R2:4:1234``."""
    return f"{a.rule}:{'' if a.key is None else a.key}:{a.raised_index}"


def _r(values: list[float | None], digits: int) -> list[float | None]:
    return [None if v is None else round(v, digits) for v in values]


def replay_window(panel: LinePanel, start: float | None, minutes: int) -> Replay:
    """Pieces of ``[start, start + minutes)`` plus up to ``LEAD_MAX`` lead pieces before them.

    ``start`` None = the first piece of the line. Raises `StartOutsideDataError`
    when it is before the first or after the last piece.
    """
    line, ds = panel.line, panel.dataset
    ts = line.timestamps
    if start is None and ts:
        start = ts[0]
    if start is None or not ts or not ts[0] <= start <= ts[-1]:
        raise StartOutsideDataError(start)
    end = start + minutes * 60
    w0 = bisect_left(ts, start)
    stop = bisect_left(ts, end)
    first = max(0, w0 - LEAD_MAX)
    shifts: list[Shift] = []
    s = shift_start(ts[first], ds.utc_offset_s)
    while s < end:
        shifts.append(Shift(shift_label(s, ds.utc_offset_s), s, s + SHIFT_S))
        s += SHIFT_S
    station_index = {st.key: k for k, st in enumerate(ds.stations)}
    state = panel.evaluation.state
    rows = slice(first, stop)
    alarms = [
        (
            alarm_id(a),
            replace(
                a,
                raised_index=a.raised_index - first,
                cleared_index=None if a.cleared_index is None else a.cleared_index - first,
                evidence_from_index=a.evidence_from_index - first,
            ),
        )
        for a in panel.evaluation.alarms
        if a.raised_index < stop and (a.cleared_index is None or a.cleared_index > first)
    ]
    return Replay(
        start_ts=start,
        end_ts=end,
        lead=w0 - first,
        shifts=shifts,
        baseline=_baseline(panel, first),
        t=[round(x - start, 3) for x in ts[rows]],
        nest=line.nests[rows],
        cavity=[None] * (stop - first) if line.mold_cavities is None else line.mold_cavities[rows],
        nok=[1 if bad else 0 for bad in line.nok[rows]],
        station=[-1 if x is None else station_index[x] for x in line.stations[rows]],
        run=state.run[rows],
        rate=_r(state.rate[rows], 4),
        nest_ratio=_r(state.nest_ratio[rows], 3),
        nest_ratio_nest=state.nest_ratio_nest[rows],
        cavity_rate=_r(state.cavity_rate[rows], 4),
        cavity_worst=state.cavity_worst[rows],
        alarms=alarms,
    )
