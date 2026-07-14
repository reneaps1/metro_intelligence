"""F7.D (MI-44): compliance engine unit tests.

Every expected value below is calculated by hand in the comment next to it,
not derived by running the engine itself (docs/testing-strategy.md's
requirement for tolerance-evaluation edge cases).
"""

from __future__ import annotations

from decimal import Decimal

from app.engines.compliance.evaluate import ENGINE_NAME, ENGINE_VERSION, SpecificationSnapshot, evaluate

BILATERAL = SpecificationSnapshot(
    nominal=Decimal("10.000"),
    lower_tol=Decimal("-0.050"),
    upper_tol=Decimal("0.050"),
    unit="mm",
)


def test_within_tolerance() -> None:
    # deviation = 10.020 - 10.000 = 0.020; -0.050 <= 0.020 <= 0.050 -> OK
    result = evaluate(Decimal("10.020"), BILATERAL)
    assert result.deviation == Decimal("0.020")
    assert result.is_ok is True
    assert "within tolerance" in result.rationale.lower()


def test_exactly_on_upper_limit_is_ok() -> None:
    # deviation = 10.050 - 10.000 = 0.050 == upper_tol -> inclusive bound -> OK
    result = evaluate(Decimal("10.050"), BILATERAL)
    assert result.deviation == Decimal("0.050")
    assert result.is_ok is True


def test_exactly_on_lower_limit_is_ok() -> None:
    # deviation = 9.950 - 10.000 = -0.050 == lower_tol -> inclusive bound -> OK
    result = evaluate(Decimal("9.950"), BILATERAL)
    assert result.deviation == Decimal("-0.050")
    assert result.is_ok is True


def test_just_over_upper_limit_is_nok() -> None:
    # deviation = 10.060 - 10.000 = 0.060 > 0.050 -> NOK, 0.010 over the limit
    result = evaluate(Decimal("10.060"), BILATERAL)
    assert result.deviation == Decimal("0.060")
    assert result.is_ok is False
    assert "0.010" in result.rationale
    assert "above the upper" in result.rationale.lower()


def test_just_under_lower_limit_is_nok() -> None:
    # deviation = 9.940 - 10.000 = -0.060 < -0.050 -> NOK, 0.010 under the limit
    result = evaluate(Decimal("9.940"), BILATERAL)
    assert result.deviation == Decimal("-0.060")
    assert result.is_ok is False
    assert "0.010" in result.rationale
    assert "below the lower" in result.rationale.lower()


def test_unilateral_upper_only_has_no_lower_bound() -> None:
    spec = SpecificationSnapshot(nominal=Decimal("5.0"), lower_tol=None, upper_tol=Decimal("0.2"), unit="mm")
    # Deviation is hugely negative (-100); with no lower_tol it can never fail
    # on that side, no matter how far below nominal the value is.
    result = evaluate(Decimal("-95.0"), spec)
    assert result.deviation == Decimal("-100.0")
    assert result.is_ok is True


def test_unilateral_upper_only_still_fails_above_limit() -> None:
    spec = SpecificationSnapshot(nominal=Decimal("5.0"), lower_tol=None, upper_tol=Decimal("0.2"), unit="mm")
    # deviation = 5.3 - 5.0 = 0.3 > 0.2 -> NOK
    result = evaluate(Decimal("5.3"), spec)
    assert result.deviation == Decimal("0.3")
    assert result.is_ok is False
    assert "above the upper" in result.rationale.lower()


def test_unilateral_lower_only_has_no_upper_bound() -> None:
    spec = SpecificationSnapshot(nominal=Decimal("5.0"), lower_tol=Decimal("-0.2"), upper_tol=None, unit="mm")
    # Deviation is hugely positive (+100); with no upper_tol it can never fail
    # on that side.
    result = evaluate(Decimal("105.0"), spec)
    assert result.deviation == Decimal("100.0")
    assert result.is_ok is True


def test_unilateral_lower_only_still_fails_below_limit() -> None:
    spec = SpecificationSnapshot(nominal=Decimal("5.0"), lower_tol=Decimal("-0.2"), upper_tol=None, unit="mm")
    # deviation = 4.7 - 5.0 = -0.3 < -0.2 -> NOK
    result = evaluate(Decimal("4.7"), spec)
    assert result.deviation == Decimal("-0.3")
    assert result.is_ok is False
    assert "below the lower" in result.rationale.lower()


def test_result_carries_engine_name_and_version() -> None:
    result = evaluate(Decimal("10.0"), BILATERAL)
    assert result.engine_name == ENGINE_NAME
    assert result.engine_version == ENGINE_VERSION
