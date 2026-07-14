"""F9.D (MI-46): risk engine unit tests.

Every expected value is calculated by hand in the comment above it
(same discipline as F7.D/F8.D's tests, per docs/testing-strategy.md).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.engines.risk.score import ENGINE_NAME, ENGINE_VERSION, ResultPoint, score_characteristic
from app.engines.spc.capability import ToleranceSpec

BILATERAL = ToleranceSpec(nominal=Decimal("10"), lower_tol=Decimal("-0.05"), upper_tol=Decimal("0.05"))


def _points(deviations: list[str], ok_flags: list[bool]) -> list[ResultPoint]:
    return [ResultPoint(deviation=Decimal(d), is_ok=ok) for d, ok in zip(deviations, ok_flags, strict=True)]


def test_stable_characteristic_scores_low() -> None:
    # 6 points, deviation 0.01 flat (all well within +/-0.05), all OK, good Cpk.
    # NOK rate: 0/6 = 0 -> contribution 0
    # Proximity: 0.01/0.05 = 0.2 for every point -> worst = 0.2 -> round(0.2*25) = 5
    # Cpk = 2.0 (capable): shortfall = max(0, 1.33-2.0) = 0 -> contribution 0
    # Trend: first/second half means both 0.01 -> shift = 0 -> contribution 0
    # Total = 0+5+0+0 = 5 -> level "low"
    points = _points(["0.01"] * 6, [True] * 6)
    result = score_characteristic(points, BILATERAL, cpk=Decimal("2.0"))

    assert result.score == 5
    assert result.level == "low"
    assert sum(f.contribution for f in result.factors) == result.score


def test_drifting_characteristic_with_recent_noks_scores_high() -> None:
    # deviations 0.01,0.02,0.03,0.04,0.06,0.06 -- last two exceed the +0.05
    # upper limit (NOK); values are drifting up over the window.
    # NOK rate: 2/6 = 1/3 -> round(40/3) = round(13.333) = 13
    # Proximity: dev/0.05 per point = 0.2,0.4,0.6,0.8,1.2,1.2 -> clipped to
    #   [0,1] -> worst = 1.0 -> round(1.0*25) = 25
    # Cpk = 0.5 (poor): shortfall = (1.33-0.5)/1.33 = 0.624060... ->
    #   round(0.624060*20) = round(12.481) = 12
    # Trend: first half [0.01,0.02,0.03] mean = 0.02; second half
    #   [0.04,0.06,0.06] mean = 0.16/3 = 0.053333...; shift = 0.033333...
    #   (= 1/30); tolerance_scale = avg(0.05,0.05) = 0.05;
    #   ratio = (1/30)/0.05 = 2/3; round((2/3)*15) = round(10.0) = 10
    # Total = 13+25+12+10 = 60 -> level "high" (>=60, <80)
    points = _points(
        ["0.01", "0.02", "0.03", "0.04", "0.06", "0.06"],
        [True, True, True, True, False, False],
    )
    result = score_characteristic(points, BILATERAL, cpk=Decimal("0.5"))

    assert result.score == 60
    assert result.level == "high"
    assert sum(f.contribution for f in result.factors) == result.score

    factor_by_label = {f.label: f.contribution for f in result.factors}
    assert factor_by_label["Historical NOK rate"] == 13
    assert factor_by_label["Proximity to tolerance limit"] == 25
    assert factor_by_label["Process capability (low Cpk)"] == 12
    assert factor_by_label["Trend toward limit"] == 10


def test_severely_out_of_control_characteristic_scores_critical() -> None:
    # All 6 points at 0.06 -- past the +0.05 limit, so all NOK; flat (no
    # trend); poor Cpk.
    # NOK rate: 6/6 = 1 -> contribution 40
    # Proximity: 0.06/0.05 = 1.2 -> clipped to 1.0 for every point -> 25
    # Cpk = 0.2: shortfall = (1.33-0.2)/1.33 = 0.849624... -> round(*20) = 17
    # Trend: both halves mean 0.06 -> shift = 0 -> contribution 0
    # Total = 40+25+17+0 = 82 -> level "critical" (>=80)
    points = _points(["0.06"] * 6, [False] * 6)
    result = score_characteristic(points, BILATERAL, cpk=Decimal("0.2"))

    assert result.score == 82
    assert result.level == "critical"


def test_improving_trend_does_not_contribute_risk() -> None:
    # Deviation is shrinking toward nominal over the window (0.04 -> 0.01):
    # first half mean 0.04, second half mean 0.01 -> the point is moving
    # *toward* nominal, not away from it, so the trend factor must be 0
    # even though the two means clearly differ.
    points = _points(
        ["0.04", "0.04", "0.04", "0.01", "0.01", "0.01"],
        [True] * 6,
    )
    result = score_characteristic(points, BILATERAL, cpk=Decimal("2.0"))
    factor_by_label = {f.label: f.contribution for f in result.factors}
    assert factor_by_label["Trend toward limit"] == 0


def test_missing_cpk_contributes_zero_and_is_labeled_insufficient_data() -> None:
    points = _points(["0.01"] * 6, [True] * 6)
    result = score_characteristic(points, BILATERAL, cpk=None)
    factor = next(f for f in result.factors if "Cpk" in f.label)
    assert factor.contribution == 0
    assert "insufficient data" in factor.label.lower()


def test_fewer_than_four_points_skips_trend_factor() -> None:
    points = _points(["0.01", "0.02", "0.03"], [True, True, True])
    result = score_characteristic(points, BILATERAL, cpk=Decimal("2.0"))
    factor = next(f for f in result.factors if "Trend" in f.label)
    assert factor.contribution == 0
    assert "insufficient data" in factor.label.lower()


def test_empty_points_raises() -> None:
    with pytest.raises(ValueError, match="at least one"):
        score_characteristic([], BILATERAL)


def test_score_is_reproducible_for_identical_inputs() -> None:
    points = _points(["0.01", "0.02", "0.03", "0.04", "0.06", "0.06"], [True, True, True, True, False, False])
    first = score_characteristic(points, BILATERAL, cpk=Decimal("0.5"))
    second = score_characteristic(points, BILATERAL, cpk=Decimal("0.5"))
    assert first.score == second.score
    assert first.level == second.level
    assert [f.contribution for f in first.factors] == [f.contribution for f in second.factors]


def test_score_carries_engine_name_and_version() -> None:
    points = _points(["0.01"] * 6, [True] * 6)
    result = score_characteristic(points, BILATERAL, cpk=Decimal("2.0"))
    assert result.engine_name == ENGINE_NAME == "risk_engine"
    assert result.engine_version == ENGINE_VERSION == "v1"
