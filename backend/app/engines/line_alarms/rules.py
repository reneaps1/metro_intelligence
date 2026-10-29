"""IQ-F14: line alarm rules replayed piece by piece (`docs/design/line-quality-panel.md`).

Four rules evaluated after each piece, in line order:

- R1 NOK streak (priority 1): trailing consecutive NOK pieces >= ``run_limit``;
  clears on the next OK piece.
- R2 Nest out of pattern (priority 2): per nest, NOK rate of its last
  ``nest_window`` pieces >= ``nest_factor`` x the pooled rate of the other
  nests' current windows, with at least ``nest_min_nok`` NOK; full window only.
- R3 High NOK rate (priority 2): NOK rate of the last ``rate_window`` line
  pieces >= ``rate_factor`` x ``p_ref``; full window only.
- R4 Mold cavity (priority 3, advisory): per mold cavity, NOK rate of its last
  ``cavity_window`` pieces >= ``cavity_factor`` x ``p_ref``; full window only,
  and only when the line carries mold cavities.

``p_ref`` is the NOK rate of the whole sequence (a hindsight reference, passed
in or computed here), so the same thresholds work on lines with very different
NOK levels. Two guards keep the rules finite and meaningful: R3/R4 need at
least one NOK in the window (a line without NOK never alarms), and the pooled
NOK count of the other nests is floored at half a piece, so the R2 ratio stays
finite when the other nests had none.

Each rule is one pass with running counters (per-piece work is O(nests) at
most), so 10^5 pieces replay in about a second of pure Python.

Pure and shadow-mode only (CLAUDE.md §2, §22): an alarm asks a person for an
action; nothing here stops a line, writes an Alert or touches measurement history.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

ENGINE_NAME = "line_alarm_engine"
ENGINE_VERSION = "v1-experimental"  # never drop "-experimental": shadow-mode only.

Rule = Literal["R1", "R2", "R3", "R4"]
PRIORITY: dict[Rule, int] = {"R1": 1, "R2": 2, "R3": 2, "R4": 3}
# Floor of the pooled NOK count of the other nests in the R2 ratio (half a piece).
REST_NOK_FLOOR = 0.5
_EPS = 1e-12


@dataclass(frozen=True)
class LineRuleConfig:
    """Rule parameters (defaults from the design document)."""

    run_limit: int = 5
    # R2/R3 were tuned on the local real dataset (IQ-F14) so the operator sees about
    # one priority-2 alarm per hour or less, not a flood; see the design document.
    nest_window: int = 100
    nest_factor: float = 3.0
    nest_min_nok: int = 25
    rate_window: int = 200
    rate_factor: float = 2.5
    cavity_window: int = 150
    cavity_factor: float = 3.0
    # Deadband (ISA-18.2): an open R2/R3/R4 alarm clears only below this share of
    # its limits, so a value hovering at the threshold does not chatter.
    clear_fraction: float = 0.75

    def __post_init__(self) -> None:
        sizes = (self.run_limit, self.nest_window, self.nest_min_nok, self.rate_window, self.cavity_window)
        if min(sizes) < 1 or min(self.nest_factor, self.rate_factor, self.cavity_factor) <= 0:
            raise ValueError("windows and limits must be positive")
        if not 0 < self.clear_fraction <= 1:
            raise ValueError("clear_fraction must be in (0, 1]")


DEFAULT_CONFIG = LineRuleConfig()


@dataclass(frozen=True)
class LineAlarm:
    """One alarm event; indices are positions in the evaluated sequence."""

    rule: Rule
    priority: int
    key: int | None  # nest (R2), mold cavity (R4), None otherwise
    raised_index: int
    raised_ts: float
    cleared_index: int | None  # None = still active at the end of the data
    cleared_ts: float | None
    evidence_from_index: int  # R1: first NOK of the streak; R2-R4: first piece of the window
    evidence_from_ts: float
    value: float  # at raise: streak length / ratio / rate
    peak: float  # max value while active (R1: final streak length)
    limit: float
    nests: tuple[int, ...]  # R1: nest of each streak piece up to the raise (in order)
    station: str | None  # first failing station of the raising piece


@dataclass(frozen=True)
class PieceState:
    """Rule state after each piece (same length as the input)."""

    run: list[int]
    rate: list[float | None]  # R3 window rate, None until full
    nest_ratio: list[float | None]  # highest R2 ratio among nests with a full window
    nest_ratio_nest: list[int | None]
    cavity_rate: list[float | None]  # highest R4 rate among cavities with a full window
    cavity_worst: list[int | None]


@dataclass(frozen=True)
class LineEvaluation:
    config: LineRuleConfig
    reference_nok_rate: float
    rate_limit: float
    cavity_limit: float
    has_mold_cavities: bool
    state: PieceState
    alarms: list[LineAlarm]


@dataclass
class _Open:
    """An alarm while it is active (mutable until it clears)."""

    rule: Rule
    key: int | None
    raised_index: int
    evidence_from_index: int
    value: float
    limit: float
    nests: tuple[int, ...] = ()
    station: str | None = None
    peak: float = field(init=False)
    cleared_index: int | None = None

    def __post_init__(self) -> None:
        self.peak = self.value


class _Windows:
    """Sliding windows of sequence indices per group, with NOK counts, pooled totals and the worst group."""

    def __init__(self, groups: int, size: int) -> None:
        self.size = size
        self.windows: list[deque[int]] = [deque() for _ in range(groups)]
        self.counts = [0] * groups
        # NOK count of each full window, -1 while not full.
        self.full_counts = [-1] * groups
        self.pooled_len = 0  # pieces in all windows
        self.pooled_nok = 0
        # Full window with most NOK (lowest group on ties), kept incrementally.
        self.worst: int | None = None

    def push(self, g: int, i: int, flags: Sequence[int]) -> None:
        w = self.windows[g]
        w.append(i)
        k = self.counts[g] + flags[i]
        self.pooled_nok += flags[i]
        if len(w) > self.size:
            out = flags[w.popleft()]
            k -= out
            self.pooled_nok -= out
        else:
            self.pooled_len += 1
        self.counts[g] = k
        if len(w) < self.size:
            return
        full = self.full_counts
        old, full[g] = full[g], k
        b = self.worst
        if b is None or k > full[b] or (k == full[b] and g < b):
            self.worst = g
        elif g == b and k < old:
            self.worst = full.index(max(full))


def _close(alarm: _Open, i: int, done: list[_Open]) -> None:
    alarm.cleared_index = i
    done.append(alarm)


def _streaks(
    flags: Sequence[int], nests: Sequence[int | None], stations: Sequence[str | None], cfg: LineRuleConfig
) -> tuple[list[int], list[_Open]]:
    """R1: trailing consecutive NOK; raises at ``run_limit``, clears on the next OK piece."""
    runs: list[int] = []
    done: list[_Open] = []
    run = 0
    alarm: _Open | None = None
    for i, bad in enumerate(flags):
        if bad:
            run += 1
            if run == cfg.run_limit:
                start = i - run + 1
                streak = tuple(x for x in nests[start : i + 1] if x is not None)
                alarm = _Open("R1", None, i, start, float(run), float(cfg.run_limit), streak, stations[i])
            elif alarm is not None:
                alarm.peak = float(run)
        else:
            if alarm is not None:
                _close(alarm, i, done)
                alarm = None
            run = 0
        runs.append(run)
    if alarm is not None:
        done.append(alarm)
    return runs, done


def _nest_rule(
    flags: Sequence[int], nests: Sequence[int | None], stations: Sequence[str | None], cfg: LineRuleConfig
) -> tuple[list[float | None], list[int | None], list[_Open]]:
    """R2: a nest's full window vs the pooled windows of the other nests (+ worst ratio per piece)."""
    keys = sorted({x for x in nests if x is not None})
    pos = {k: p for p, k in enumerate(keys)}
    size, min_nok, factor = cfg.nest_window, cfg.nest_min_nok, cfg.nest_factor - _EPS
    keep_nok, keep_factor = min_nok * cfg.clear_fraction, cfg.nest_factor * cfg.clear_fraction - _EPS
    win = _Windows(len(keys), size)
    counts, full = win.counts, win.full_counts
    hot: set[int] = set()  # full windows with >= nest_min_nok NOK: the only nests that can alarm
    open_: dict[int, _Open] = {}
    done: list[_Open] = []
    ratios: list[float | None] = []
    worst_nests: list[int | None] = []
    for i, nest in enumerate(nests):
        if nest is not None:
            g = pos[nest]
            win.push(g, i, flags)
            if full[g] >= min_nok:
                hot.add(g)
            else:
                hot.discard(g)
        # Pieces of the other nests in the comparison: equal for every full window, never shrinks.
        rest_len = win.pooled_len - size
        if rest_len <= 0:
            ratios.append(None)
            worst_nests.append(None)
            continue
        pooled = win.pooled_nok
        # Every ratio moves with the pooled rest, so candidates are re-checked at each piece.
        for g in hot.union(open_) if hot or open_ else ():
            k = counts[g]
            ratio = k * rest_len / (size * max(pooled - k, REST_NOK_FLOOR))
            alarm = open_.get(g)
            if alarm is None:
                if k >= min_nok and ratio >= factor:
                    open_[g] = _Open(
                        "R2", keys[g], i, win.windows[g][0], ratio, cfg.nest_factor, (), stations[i]
                    )
            elif k >= keep_nok and ratio >= keep_factor:
                alarm.peak = max(alarm.peak, ratio)
            else:
                _close(open_.pop(g), i, done)
        # The ratio grows with the nest's own count: the worst nest is the full window with most NOK.
        b = win.worst
        if b is None:
            ratios.append(None)
            worst_nests.append(None)
        else:
            ratios.append(counts[b] * rest_len / (size * max(pooled - counts[b], REST_NOK_FLOOR)))
            worst_nests.append(keys[b])
    done.extend(open_.values())
    return ratios, worst_nests, done


def _rate_rule(
    flags: Sequence[int], stations: Sequence[str | None], cfg: LineRuleConfig, limit: float
) -> tuple[list[float | None], list[_Open]]:
    """R3: NOK rate of the last ``rate_window`` line pieces vs ``rate_factor`` x ``p_ref``."""
    size = cfg.rate_window
    rates: list[float | None] = []
    done: list[_Open] = []
    alarm: _Open | None = None
    k = 0
    for i, bad in enumerate(flags):
        k += bad
        if i >= size:
            k -= flags[i - size]
        if i < size - 1:
            rates.append(None)
            continue
        rate = k / size
        rates.append(rate)
        if alarm is None:
            if k > 0 and rate >= limit - _EPS:
                alarm = _Open("R3", None, i, i - size + 1, rate, limit, (), stations[i])
        elif rate >= limit * cfg.clear_fraction - _EPS:
            alarm.peak = max(alarm.peak, rate)
        else:
            _close(alarm, i, done)
            alarm = None
    if alarm is not None:
        done.append(alarm)
    return rates, done


def _cavity_rule(
    flags: Sequence[int],
    molds: Sequence[int | None],
    stations: Sequence[str | None],
    cfg: LineRuleConfig,
    limit: float,
) -> tuple[list[float | None], list[int | None], list[_Open]]:
    """R4: a mold cavity's full window vs ``cavity_factor`` x ``p_ref`` (+ worst cavity per piece)."""
    keys = sorted({x for x in molds if x is not None})
    pos = {k: p for p, k in enumerate(keys)}
    size = cfg.cavity_window
    win = _Windows(len(keys), size)
    open_: dict[int, _Open] = {}
    done: list[_Open] = []
    rates: list[float | None] = []
    worst: list[int | None] = []
    for i, cavity in enumerate(molds):
        if cavity is not None:
            c = pos[cavity]
            win.push(c, i, flags)
            # Only the cavity's own pieces change its window (-1 while not full).
            k = win.full_counts[c]
            alarm = open_.get(c)
            if alarm is None:
                if k > 0 and k / size >= limit - _EPS:
                    open_[c] = _Open("R4", cavity, i, win.windows[c][0], k / size, limit, (), stations[i])
            elif k / size >= limit * cfg.clear_fraction - _EPS:
                alarm.peak = max(alarm.peak, k / size)
            else:
                _close(open_.pop(c), i, done)
        b = win.worst
        rates.append(None if b is None else win.full_counts[b] / size)
        worst.append(None if b is None else keys[b])
    done.extend(open_.values())
    return rates, worst, done


def evaluate_line(
    timestamps: Sequence[float],
    nests: Sequence[int | None],
    mold_cavities: Sequence[int | None] | None,
    nok: Sequence[bool],
    stations: Sequence[str | None],
    config: LineRuleConfig = DEFAULT_CONFIG,
    reference_nok_rate: float | None = None,
) -> LineEvaluation:
    """Replay R1-R4 over a line sequence.

    Args:
        timestamps: Piece time (epoch seconds), non-decreasing (line order).
        nests: Nest of each piece (None = not attributed to a nest).
        mold_cavities: Mold cavity of each piece, or None when the line has none.
        nok: Verdict of each piece (True = NOK).
        stations: First failing station of each piece (None = none failed / no stations).
        config: Rule parameters.
        reference_nok_rate: ``p_ref``; None = NOK rate of this whole sequence.

    Returns:
        Per-piece rule state and every alarm event, in raise order.

    Raises:
        ValueError: On inconsistent lengths, unordered timestamps or a rate outside [0, 1].
    """
    n = len(timestamps)
    columns = [nests, nok, stations, *([mold_cavities] if mold_cavities is not None else [])]
    if any(len(col) != n for col in columns):
        raise ValueError("all input sequences must have the same length")
    if any(b < a for a, b in zip(timestamps, timestamps[1:], strict=False)):
        raise ValueError("timestamps must be in line order (non-decreasing)")
    flags = [1 if x else 0 for x in nok]
    p_ref = (sum(flags) / n if n else 0.0) if reference_nok_rate is None else reference_nok_rate
    if not 0.0 <= p_ref <= 1.0:
        raise ValueError("reference_nok_rate must be within [0, 1]")
    rate_limit = config.rate_factor * p_ref
    cavity_limit = config.cavity_factor * p_ref
    has_molds = mold_cavities is not None and any(c is not None for c in mold_cavities)

    runs, r1 = _streaks(flags, nests, stations, config)
    ratios, ratio_nests, r2 = _nest_rule(flags, nests, stations, config)
    rates, r3 = _rate_rule(flags, stations, config, rate_limit)
    cavity_rates: list[float | None] = [None] * n
    cavity_worst: list[int | None] = [None] * n
    r4: list[_Open] = []
    if has_molds and mold_cavities is not None:
        cavity_rates, cavity_worst, r4 = _cavity_rule(flags, mold_cavities, stations, config, cavity_limit)

    order = {"R1": 0, "R2": 1, "R3": 2, "R4": 3}
    events = sorted(
        [*r1, *r2, *r3, *r4], key=lambda a: (a.raised_index, order[a.rule], -1 if a.key is None else a.key)
    )
    alarms = [
        LineAlarm(
            rule=a.rule,
            priority=PRIORITY[a.rule],
            key=a.key,
            raised_index=a.raised_index,
            raised_ts=timestamps[a.raised_index],
            cleared_index=a.cleared_index,
            cleared_ts=None if a.cleared_index is None else timestamps[a.cleared_index],
            evidence_from_index=a.evidence_from_index,
            evidence_from_ts=timestamps[a.evidence_from_index],
            value=a.value,
            peak=a.peak,
            limit=a.limit,
            nests=a.nests,
            station=a.station,
        )
        for a in events
    ]
    return LineEvaluation(
        config=config,
        reference_nok_rate=p_ref,
        rate_limit=rate_limit,
        cavity_limit=cavity_limit,
        has_mold_cavities=has_molds,
        state=PieceState(runs, rates, ratios, ratio_nests, cavity_rates, cavity_worst),
        alarms=alarms,
    )
