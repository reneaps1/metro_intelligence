"""F8.D (MI-45): SPC engine unit tests.

Every expected value is calculated by hand in the comment above it
(docs/testing-strategy.md's explicit requirement for Cp/Cpk/control-limit
reference vectors), not derived by running the engine itself.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.engines.spc.capability import ENGINE_NAME as CAPABILITY_ENGINE_NAME
from app.engines.spc.capability import ENGINE_VERSION as CAPABILITY_ENGINE_VERSION
from app.engines.spc.capability import ToleranceSpec, cp, cpk
from app.engines.spc.control_limits import ENGINE_NAME, ENGINE_VERSION, individuals_moving_range_limits


def _dec_list(values: list[str]) -> list[Decimal]:
    return [Decimal(v) for v in values]


# --- Cp/Cpk ---------------------------------------------------------------

BILATERAL = ToleranceSpec(nominal=Decimal("10"), lower_tol=Decimal("-0.05"), upper_tol=Decimal("0.05"))


def test_cp_and_cpk_equal_when_process_is_centered() -> None:
    # values: 9.98, 10.02, 10.00, 9.99, 10.01 -> mean = 50.00/5 = 10.00
    # deviations from mean: -0.02, 0.02, 0.00, -0.01, 0.01
    # sum of squares = 0.0004+0.0004+0+0.0001+0.0001 = 0.0010
    # sample variance (n-1=4) = 0.00025 -> sample stdev = sqrt(0.00025) = 0.015811388...
    values = _dec_list(["9.98", "10.02", "10.00", "9.99", "10.01"])
    # Cp = (USL-LSL)/(6*s) = 0.10 / (6*0.015811388) = 1.054093
    assert float(cp(values, BILATERAL)) == pytest.approx(1.054093, rel=1e-4)
    # Centered process: Cpk == Cp (both sides equidistant from the mean).
    assert float(cpk(values, BILATERAL)) == pytest.approx(1.054093, rel=1e-4)


def test_cpk_is_lower_than_cp_when_process_is_off_center() -> None:
    # Same spread as the centered case above (deviations from the new mean
    # are -0.02, 0.00, 0.01, -0.01, 0.02 -- identical set, same stdev), but
    # mean = (10.00+10.02+10.03+10.01+10.04)/5 = 50.10/5 = 10.02.
    values = _dec_list(["10.00", "10.02", "10.03", "10.01", "10.04"])
    # Cp only depends on spread and spec width, unchanged from the centered case.
    assert float(cp(values, BILATERAL)) == pytest.approx(1.054093, rel=1e-4)
    # Cpk: min((10.05-10.02), (10.02-9.95)) / (3*0.015811388)
    #    = min(0.03, 0.07) / 0.0474342 = 0.03/0.0474342 = 0.632456
    result = cpk(values, BILATERAL)
    assert float(result) == pytest.approx(0.632456, rel=1e-4)
    assert float(result) < float(cp(values, BILATERAL))


def test_cp_raises_for_unilateral_tolerance() -> None:
    spec = ToleranceSpec(nominal=Decimal("10"), lower_tol=None, upper_tol=Decimal("0.3"))
    values = _dec_list(["10.0", "10.1", "10.2", "10.0", "10.2"])
    with pytest.raises(ValueError, match="unilateral"):
        cp(values, spec)


def test_cpk_unilateral_upper_only() -> None:
    # mean = (10.0+10.1+10.2+10.0+10.2)/5 = 50.5/5 = 10.10
    # deviations: -0.10, 0.00, 0.10, -0.10, 0.10 -> sum sq = 0.04
    # sample variance (n-1=4) = 0.01 -> sample stdev = 0.1 (exact)
    # Cpk = (USL-mean)/(3s) = (10.3-10.10)/(0.3) = 0.20/0.3 = 0.666...
    spec = ToleranceSpec(nominal=Decimal("10"), lower_tol=None, upper_tol=Decimal("0.3"))
    values = _dec_list(["10.0", "10.1", "10.2", "10.0", "10.2"])
    assert float(cpk(values, spec)) == pytest.approx(2 / 3, rel=1e-4)


def test_cpk_unilateral_lower_only() -> None:
    # Same values/stdev as above (mean=10.10, s=0.1), mirrored tolerance:
    # Cpk = (mean-LSL)/(3s) = (10.10-9.70)/0.3 = 0.40/0.3 = 1.333...
    spec = ToleranceSpec(nominal=Decimal("10"), lower_tol=Decimal("-0.3"), upper_tol=None)
    values = _dec_list(["10.0", "10.1", "10.2", "10.0", "10.2"])
    assert float(cpk(values, spec)) == pytest.approx(4 / 3, rel=1e-4)


def test_cp_raises_on_zero_variance() -> None:
    values = _dec_list(["10.0", "10.0", "10.0"])
    with pytest.raises(ValueError, match="zero"):
        cp(values, BILATERAL)


def test_capability_functions_carry_engine_name_and_version() -> None:
    assert CAPABILITY_ENGINE_NAME == "spc_engine"
    assert CAPABILITY_ENGINE_VERSION == "v1"


# --- I-MR control limits ----------------------------------------------------


def test_individuals_moving_range_limits_hand_calculated() -> None:
    # values: 10, 12, 11, 13, 10
    # moving ranges: |12-10|=2, |11-12|=1, |13-11|=2, |10-13|=3 -> MRbar = 8/4 = 2.0
    # xbar = (10+12+11+13+10)/5 = 56/5 = 11.2
    # individuals UCL/LCL = xbar +/- E2*MRbar = 11.2 +/- 2.660*2.0 = 11.2 +/- 5.32
    # MR chart UCL = D4*MRbar = 3.267*2.0 = 6.534; LCL = 0 (D3=0)
    values = _dec_list(["10", "12", "11", "13", "10"])
    limits = individuals_moving_range_limits(values)

    assert limits.center_line == Decimal("11.2")
    assert limits.mr_center_line == Decimal("2.0")
    assert limits.individuals_ucl == Decimal("16.52")
    assert limits.individuals_lcl == Decimal("5.88")
    assert limits.mr_ucl == Decimal("6.534")
    assert limits.mr_lcl == Decimal("0")


def test_individuals_moving_range_limits_stable_series_stays_within_bounds() -> None:
    # A tight, stable series: 10.00, 10.01, 9.99, 10.02, 10.00, 9.98, 10.01
    # -- every point should fall within its own computed control limits
    # (this is what "stable" means for a series that generated the limits).
    values = _dec_list(["10.00", "10.01", "9.99", "10.02", "10.00", "9.98", "10.01"])
    limits = individuals_moving_range_limits(values)
    for value in values:
        assert limits.individuals_lcl <= value <= limits.individuals_ucl


def test_control_limits_carry_engine_name_and_version() -> None:
    limits = individuals_moving_range_limits(_dec_list(["10", "11"]))
    assert limits.engine_name == ENGINE_NAME == "spc_engine"
    assert limits.engine_version == ENGINE_VERSION == "v1"
