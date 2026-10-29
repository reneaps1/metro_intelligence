"""IQ-F12: retrospective evaluation of a per-group NOK alarm (cavity or nest).

Rule: a group (mold cavity, nest...) is "in alarm" while at least ``k`` of
its last ``n`` pieces are NOK. It only reads pieces already inspected, so it
can flag a group that has started to fail; it cannot foresee the first NOK.

The evaluation answers what a quality manager asks of such an alarm:

- When would each group have alarmed first?
- How many NOK pieces of that group came *after* its first alarm (the share a
  reaction could have protected), and how many before (unavoidable for this rule)?
- What is the review burden: OK pieces produced while the group was in alarm?

The scope can start at a given time (e.g. the restart after the longest stop),
so a new episode is evaluated on its own. Pure and shadow-mode only
(CLAUDE.md §22): nothing here raises a real alert or acts on production.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

ENGINE_NAME = "group_alarm_engine"
ENGINE_VERSION = "v1-experimental"  # never drop "-experimental": shadow-mode only.


@dataclass(frozen=True)
class GroupAlarm:
    group: int
    pieces: int
    nok: int
    first_alarm_ts: float | None
    # NOK pieces of this group after (and including the piece of) its first alarm.
    nok_after_first_alarm: int
    # Separate alarm periods (enter/leave the alarm state) -- a proxy for re-alarms.
    alarm_runs: int
    # Pieces inspected while the group was in alarm, by verdict.
    nok_in_alarm: int
    ok_in_alarm: int


@dataclass(frozen=True)
class AlarmEvaluation:
    groups: list[GroupAlarm]
    pieces: int
    nok: int
    nok_after_first_alarm: int
    groups_alarmed: int
    first_alarm_ts: float | None
    ok_in_alarm: int


def evaluate_group_alarms(
    timestamps: Sequence[float],
    groups: Sequence[int | None],
    nok: Sequence[bool],
    k: int,
    n: int,
    since: float | None = None,
) -> AlarmEvaluation:
    """Replay the rule over pieces in time order (``timestamps`` ascending).

    Args:
        timestamps: Piece time (epoch seconds), ascending.
        groups: Group of each piece (None = excluded).
        nok: Verdict of each piece (True = NOK).
        k: NOK pieces needed in the window.
        n: Window size, in pieces of the same group.
        since: Only pieces at or after this time are evaluated (history before is ignored).

    Raises:
        ValueError: On inconsistent lengths or ``k > n`` / non-positive sizes.
    """
    if not (len(timestamps) == len(groups) == len(nok)):
        raise ValueError("timestamps, groups and nok must have the same length")
    if n < 1 or k < 1 or k > n:
        raise ValueError("require 1 <= k <= n")
    windows: dict[int, deque[bool]] = {}
    counts: dict[int, int] = {}
    stats: dict[int, list[float | int | None]] = {}
    in_alarm: dict[int, bool] = {}
    for ts, g, bad in zip(timestamps, groups, nok, strict=True):
        if g is None or (since is not None and ts < since):
            continue
        w = windows.setdefault(g, deque())
        w.append(bad)
        counts[g] = counts.get(g, 0) + bad
        if len(w) > n:
            counts[g] -= w.popleft()
        # [pieces, nok, first_alarm_ts, nok_after, runs, nok_in_alarm, ok_in_alarm]
        st = stats.setdefault(g, [0, 0, None, 0, 0, 0, 0])
        st[0] += 1  # type: ignore[operator]
        st[1] += bad  # type: ignore[operator]
        alarm = counts[g] >= k
        if alarm and not in_alarm.get(g, False):
            st[4] += 1  # type: ignore[operator]
            if st[2] is None:
                st[2] = ts
        in_alarm[g] = alarm
        if st[2] is not None and bad:
            st[3] += 1  # type: ignore[operator]
        if alarm:
            if bad:
                st[5] += 1  # type: ignore[operator]
            else:
                st[6] += 1  # type: ignore[operator]
    rows = [
        GroupAlarm(
            group=g,
            pieces=int(st[0]),  # type: ignore[arg-type]
            nok=int(st[1]),  # type: ignore[arg-type]
            first_alarm_ts=None if st[2] is None else float(st[2]),
            nok_after_first_alarm=int(st[3]),  # type: ignore[arg-type]
            alarm_runs=int(st[4]),  # type: ignore[arg-type]
            nok_in_alarm=int(st[5]),  # type: ignore[arg-type]
            ok_in_alarm=int(st[6]),  # type: ignore[arg-type]
        )
        for g, st in stats.items()
    ]
    rows.sort(key=lambda r: (-r.nok, r.group))
    firsts = [r.first_alarm_ts for r in rows if r.first_alarm_ts is not None]
    return AlarmEvaluation(
        groups=rows,
        pieces=sum(r.pieces for r in rows),
        nok=sum(r.nok for r in rows),
        nok_after_first_alarm=sum(r.nok_after_first_alarm for r in rows),
        groups_alarmed=len(firsts),
        first_alarm_ts=min(firsts) if firsts else None,
        ok_in_alarm=sum(r.ok_in_alarm for r in rows),
    )


def longest_gap(timestamps: Sequence[float]) -> tuple[float, float] | None:
    """(last piece before, first piece after) the longest stretch without pieces."""
    best: tuple[float, float] | None = None
    for a, b in zip(timestamps, timestamps[1:], strict=False):
        if best is None or b - a > best[1] - best[0]:
            best = (a, b)
    return best
