"""IQ-F4: ordinary least squares and Pearson correlation (pure, no numpy).

Undefined statistics are returned as ``None`` instead of a misleading number:
fewer than 3 pairs, or a constant series (zero variance), has no meaningful
correlation.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

MIN_PAIRS = 3


@dataclass(frozen=True)
class LinearFit:
    n: int
    pearson_r: float | None
    slope: float | None
    intercept: float | None
    r_squared: float | None


def linear_fit(xs: Sequence[float], ys: Sequence[float]) -> LinearFit:
    """Fit ``y = intercept + slope * x`` by least squares.

    Args:
        xs: Predictor values.
        ys: Response values, paired index-by-index with ``xs``.

    Returns:
        The fit; statistics that are undefined for the input are ``None``.

    Raises:
        ValueError: if the sequences differ in length.
    """
    n = len(xs)
    if n != len(ys):
        raise ValueError("xs and ys must have the same length")
    if n < MIN_PAIRS:
        return LinearFit(n, None, None, None, None)

    mean_x = math.fsum(xs) / n
    mean_y = math.fsum(ys) / n
    sxx = math.fsum((x - mean_x) ** 2 for x in xs)
    syy = math.fsum((y - mean_y) ** 2 for y in ys)
    sxy = math.fsum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))

    if sxx == 0.0:
        return LinearFit(n, None, None, None, None)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    if syy == 0.0:
        # y is constant: the fit is exact but correlation is undefined.
        return LinearFit(n, None, slope, intercept, None)
    r = max(-1.0, min(1.0, sxy / math.sqrt(sxx * syy)))
    return LinearFit(n, r, slope, intercept, r * r)
