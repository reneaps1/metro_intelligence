"""Pure time-series downsampling helpers (IQ-F2).

Min/max bucketing keeps every bucket's extremes, so peaks, spikes and short
alarm pulses survive a zoomed-out view -- unlike plain decimation, which would
silently drop them and make a chart misleading.
"""

from __future__ import annotations

from collections.abc import Sequence

Point = tuple[float, float]


def minmax_downsample(points: Sequence[Point], max_points: int) -> list[Point]:
    """Reduce time-ordered ``(t, value)`` points to at most ``max_points``.

    Points are split into ``max_points // 2`` equal-count buckets; each bucket
    contributes its minimum and maximum (in time order, once if they coincide).

    Args:
        points: Points sorted by time.
        max_points: Upper bound on the returned length; must be >= 2.

    Returns:
        The input unchanged if it already fits, otherwise the min/max envelope.
    """
    if max_points < 2:
        raise ValueError("max_points must be >= 2")
    n = len(points)
    if n <= max_points:
        return list(points)

    buckets = max_points // 2
    out: list[Point] = []
    for b in range(buckets):
        lo = b * n // buckets
        hi = (b + 1) * n // buckets
        if lo >= hi:
            continue
        i_min = min(range(lo, hi), key=lambda i: points[i][1])
        i_max = max(range(lo, hi), key=lambda i: points[i][1])
        if i_min == i_max:
            out.append(points[i_min])
        else:
            first, second = sorted((i_min, i_max))
            out.append(points[first])
            out.append(points[second])
    return out
