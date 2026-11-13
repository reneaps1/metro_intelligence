"""IQ-F4: least squares / Pearson engine against hand-calculated vectors."""

from __future__ import annotations

import random

import pytest
from app.engines.statistics import linear_fit


def test_perfect_line() -> None:
    xs = [0.0, 1.0, 2.0, 3.0, 4.0]
    fit = linear_fit(xs, [1.0 + 2.0 * x for x in xs])
    assert fit.n == 5
    assert fit.slope == pytest.approx(2.0)
    assert fit.intercept == pytest.approx(1.0)
    assert fit.pearson_r == pytest.approx(1.0)
    assert fit.r_squared == pytest.approx(1.0)


def test_perfect_negative_line() -> None:
    xs = [1.0, 2.0, 3.0]
    fit = linear_fit(xs, [10.0 - 3.0 * x for x in xs])
    assert fit.slope == pytest.approx(-3.0)
    assert fit.pearson_r == pytest.approx(-1.0)


def test_hand_calculated_example() -> None:
    # x̄=3, ȳ=4, Sxx=10, Sxy=6, Syy=6 -> b=0.6, a=2.2, r=6/sqrt(60)=0.7746, R²=0.6
    fit = linear_fit([1.0, 2.0, 3.0, 4.0, 5.0], [2.0, 4.0, 5.0, 4.0, 5.0])
    assert fit.slope == pytest.approx(0.6)
    assert fit.intercept == pytest.approx(2.2)
    assert fit.pearson_r == pytest.approx(0.774597, abs=1e-6)
    assert fit.r_squared == pytest.approx(0.6)


def test_independent_noise_has_near_zero_correlation() -> None:
    rng = random.Random(7)
    xs = [rng.gauss(0, 1) for _ in range(5000)]
    ys = [rng.gauss(0, 1) for _ in range(5000)]
    assert abs(linear_fit(xs, ys).pearson_r or 1.0) < 0.05


def test_undefined_statistics_are_none() -> None:
    assert linear_fit([1.0, 2.0], [1.0, 2.0]).pearson_r is None  # too few pairs
    constant_x = linear_fit([3.0, 3.0, 3.0], [1.0, 2.0, 3.0])
    assert constant_x.slope is None and constant_x.pearson_r is None
    constant_y = linear_fit([1.0, 2.0, 3.0], [5.0, 5.0, 5.0])
    assert constant_y.slope == pytest.approx(0.0)
    assert constant_y.intercept == pytest.approx(5.0)
    assert constant_y.pearson_r is None and constant_y.r_squared is None


def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        linear_fit([1.0, 2.0, 3.0], [1.0, 2.0])
