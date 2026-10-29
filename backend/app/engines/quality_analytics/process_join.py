"""IQ-F13 "Vista A": join inspected pieces with process cycles by time buckets (pure).

There is no cycle/piece traceability between the two sources, so the join is
illustrative: per bucket of plant time, ``x`` is the mean per-cycle value of
the cycles that START in the lagged bucket and ``y`` is the NOK rate of the
pieces inspected in the bucket. A positive lag means the process precedes
the inspection: ``x`` comes from ``[b - lag, b - lag + bucket)``.

Buckets are integer indices on the plant-time grid (``(ts + utc_offset) //
bucket``), so lags that are whole buckets pair indices exactly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.engines.statistics import LinearFit, linear_fit

MIN_BUCKET_PIECES = 50
MIN_BUCKET_CYCLES = 5
# Fewest counted buckets for a lag to compete for the best lag.
MIN_LAG_BUCKETS = 10


@dataclass(frozen=True)
class JoinBucket:
    start_ts: float  # UTC epoch seconds of the bucket start
    x: float
    y: float
    pieces: int
    cycles: int


@dataclass(frozen=True)
class JoinLagScore:
    lag_buckets: int
    n: int
    r: float | None


@dataclass(frozen=True)
class TimeJoin:
    buckets: list[JoinBucket]
    fit: LinearFit


def bucket_index(ts: float, bucket_s: int, utc_offset_s: int) -> int:
    """Index of the plant-time bucket containing ``ts``."""
    return int((ts + utc_offset_s) // bucket_s)


def piece_counts(
    timestamps: Sequence[float], nok: Sequence[bool], bucket_s: int, utc_offset_s: int
) -> dict[int, tuple[int, int]]:
    """(pieces, NOK pieces) per bucket index."""
    counts: dict[int, list[int]] = {}
    for ts, bad in zip(timestamps, nok, strict=True):
        entry = counts.setdefault(bucket_index(ts, bucket_s, utc_offset_s), [0, 0])
        entry[0] += 1
        entry[1] += bad
    return {b: (n, k) for b, (n, k) in counts.items()}


def cycle_sums(
    starts: Sequence[float], values: Sequence[float], bucket_s: int, utc_offset_s: int
) -> dict[int, tuple[float, int]]:
    """(sum of per-cycle values, cycles) per bucket index of the cycle START."""
    sums: dict[int, list[float]] = {}
    for ts, value in zip(starts, values, strict=True):
        entry = sums.setdefault(bucket_index(ts, bucket_s, utc_offset_s), [0.0, 0.0])
        entry[0] += value
        entry[1] += 1
    return {b: (s, int(n)) for b, (s, n) in sums.items()}


def join_at_lag(
    pieces: dict[int, tuple[int, int]],
    cycles: dict[int, tuple[float, int]],
    lag_buckets: int,
    bucket_s: int,
    utc_offset_s: int,
) -> TimeJoin:
    """Counted buckets in time order and their OLS fit ``y = intercept + slope * x``.

    A bucket counts with at least ``MIN_BUCKET_PIECES`` pieces and ``MIN_BUCKET_CYCLES``
    cycles in its lagged bucket.
    """
    rows: list[JoinBucket] = []
    for b in sorted(pieces):
        n_pieces, nok = pieces[b]
        if n_pieces < MIN_BUCKET_PIECES:
            continue
        total, n_cycles = cycles.get(b - lag_buckets, (0.0, 0))
        if n_cycles < MIN_BUCKET_CYCLES:
            continue
        rows.append(
            JoinBucket(
                float(b * bucket_s - utc_offset_s), total / n_cycles, nok / n_pieces, n_pieces, n_cycles
            )
        )
    return TimeJoin(rows, linear_fit([r.x for r in rows], [r.y for r in rows]))


def lag_scan(
    pieces: dict[int, tuple[int, int]],
    cycles: dict[int, tuple[float, int]],
    lags_buckets: Sequence[int],
    bucket_s: int,
    utc_offset_s: int,
) -> list[JoinLagScore]:
    """Pearson r and counted buckets at every lag."""
    scores = []
    for lag in lags_buckets:
        fit = join_at_lag(pieces, cycles, lag, bucket_s, utc_offset_s).fit
        scores.append(JoinLagScore(lag, fit.n, fit.pearson_r))
    return scores


def best_lag(scan: Sequence[JoinLagScore]) -> int | None:
    """Lag with the largest |r| among lags with >= ``MIN_LAG_BUCKETS`` buckets (ties: smallest |lag|)."""
    eligible = [s for s in scan if s.r is not None and s.n >= MIN_LAG_BUCKETS]
    if not eligible:
        return None
    return max(eligible, key=lambda s: (abs(s.r or 0.0), -abs(s.lag_buckets))).lag_buckets
