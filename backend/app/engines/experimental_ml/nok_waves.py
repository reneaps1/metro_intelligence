"""IQ-F7: NOK waves -- per-episode evaluation of a persistence alert rule.

A NOK "wave" is a temporary period in which a machine produces NOK pieces far
above its usual rate. Two different questions are easy to mix up:

- *Detecting persistence*: a wave has started and the rule notices it while
  it is still running ("the next groups will probably be NOK too").
- *Predicting the start*: the rule alerts before the first NOK of the wave.

The persistence rule here ("at least ``threshold`` NOK pieces in the last
``window`` inspection groups") can only do the first by construction: it
reads past NOK pieces and nothing else. Evaluating it per independent
episode -- not per overlapping window -- makes that visible: anticipated
episodes, detection delay, share of the wave still ahead when the alert
fires, and false alarm events outside any wave.

Pure: the caller supplies the ordered group series and the episodes (known
ground truth for the synthetic dataset). Shadow-mode only (CLAUDE.md §22):
nothing here raises a real Alert or acts on production.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import Literal

ENGINE_NAME = "nok_wave_engine"
ENGINE_VERSION = "v1-experimental"  # never drop "-experimental": shadow-mode only.

EpisodeStatus = Literal["anticipated", "detected", "missed"]


@dataclass(frozen=True)
class GroupPoint:
    """One inspection group (shot) of one machine, in time order."""

    ts: float
    pieces: int
    nok_pieces: int


@dataclass(frozen=True)
class Episode:
    """Inclusive group indices of a wave in the series."""

    start: int
    end: int


@dataclass(frozen=True)
class EpisodeResult:
    start: int
    end: int
    status: EpisodeStatus
    first_alert: int | None
    # Groups from the wave start to the first alert (negative = before the start).
    delay_groups: int | None
    # Share of the wave's groups from the first alert on (what an alert could still protect).
    remaining_share: float | None


@dataclass(frozen=True)
class WaveEvaluation:
    episodes: list[EpisodeResult]
    alert_events: list[tuple[int, int]]  # inclusive (first, last) group index of each alert run
    false_alarm_events: int

    @property
    def anticipated(self) -> int:
        return sum(1 for e in self.episodes if e.status == "anticipated")

    @property
    def detected(self) -> int:
        return sum(1 for e in self.episodes if e.status == "detected")

    @property
    def missed(self) -> int:
        return sum(1 for e in self.episodes if e.status == "missed")


def persistence_alerts(series: list[GroupPoint], window: int, threshold: int) -> list[int]:
    """Indices where the last ``window`` groups (current one included) hold at
    least ``threshold`` NOK pieces. Uses only past and present groups."""
    if window < 1 or threshold < 1:
        raise ValueError("window and threshold must be >= 1")
    alerts: list[int] = []
    running = 0
    for i, point in enumerate(series):
        running += point.nok_pieces
        if i >= window:
            running -= series[i - window].nok_pieces
        if running >= threshold:
            alerts.append(i)
    return alerts


def alert_runs(alerts: list[int]) -> list[tuple[int, int]]:
    """Debounce: contiguous alert indices form one alert event."""
    runs: list[tuple[int, int]] = []
    for i in sorted(alerts):
        if runs and i == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], i)
        else:
            runs.append((i, i))
    return runs


def evaluate_episodes(alerts: list[int], episodes: list[Episode], horizon: int) -> WaveEvaluation:
    """Per-episode evaluation.

    An episode is *anticipated* if an alert falls in ``[start - horizon, start)``,
    *detected* if the first alert falls in ``[start, end]``, *missed* otherwise.
    An alert event (contiguous run) that touches no ``[start - horizon, end]``
    span is a false alarm.
    """
    ordered = sorted(alerts)
    results: list[EpisodeResult] = []
    for ep in episodes:
        # First alert in [start - horizon, end] (binary search: real series hold 10^5 groups).
        pos = bisect_left(ordered, ep.start - horizon)
        first = ordered[pos] if pos < len(ordered) and ordered[pos] <= ep.end else None
        if first is None:
            results.append(EpisodeResult(ep.start, ep.end, "missed", None, None, None))
            continue
        length = ep.end - ep.start + 1
        status: EpisodeStatus = "anticipated" if first < ep.start else "detected"
        remaining = (ep.end - max(first, ep.start) + 1) / length
        results.append(EpisodeResult(ep.start, ep.end, status, first, first - ep.start, remaining))

    runs = alert_runs(ordered)
    false_alarms = sum(
        1 for a, b in runs if not any(b >= ep.start - horizon and a <= ep.end for ep in episodes)
    )
    return WaveEvaluation(episodes=results, alert_events=runs, false_alarm_events=false_alarms)


def retrospective_episodes(
    series: list[GroupPoint], window: int, threshold: int, merge_gap: int | None = None
) -> list[Episode]:
    """Episodes of a REAL series, labelled with hindsight (IQ-F12).

    Real data has no injected ground truth, so an episode is defined from the
    future on purpose -- only to *label* the evaluation, never as a feature:
    group ``i`` is "in a wave" when the ``window`` groups starting at ``i``
    hold at least ``threshold`` NOK pieces. Contiguous in-wave groups form an
    episode; episodes closer than ``merge_gap`` groups (default ``window``)
    are merged, so one long wave is not counted as many.
    """
    if window < 1 or threshold < 1:
        raise ValueError("window and threshold must be >= 1")
    gap = window if merge_gap is None else merge_gap
    n = len(series)
    noks = [p.nok_pieces for p in series]
    runs: list[list[int]] = []  # [first in-wave index, last in-wave index]
    running = sum(noks[:window])
    for i in range(n):
        if i:
            running -= noks[i - 1]
            if i + window - 1 < n:
                running += noks[i + window - 1]
        if running >= threshold:
            if runs and i - runs[-1][1] <= gap:
                runs[-1][1] = i
            else:
                runs.append([i, i])
    # The last in-wave index still looks `window` groups ahead: the wave lasts until then.
    return [Episode(a, min(n - 1, b + window - 1)) for a, b in runs]
