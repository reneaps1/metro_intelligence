"""F8.D (MI-45): process capability indices (Cp/Cpk), pure engine functions.

CLAUDE.md §3: no DB access; the caller loads the measurement values and the
specification. Sample standard deviation (n-1, Bessel's correction) is used
throughout -- this is the "overall" capability estimate. It's a different
(and simpler) sigma estimate than the moving-range-based one control_limits.py
uses; for a stable individuals process the two are close, but they are not
interchangeable and this module does not attempt to reconcile them.

Cp requires a two-sided tolerance (it's the ratio of spec width to process
spread) and is mathematically undefined for a unilateral characteristic.
Cpk handles the unilateral case (same convention as F7.D's compliance
engine): whichever tolerance side is present is evaluated; a missing side is
simply not a candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ENGINE_NAME = "spc_engine"
ENGINE_VERSION = "v1"


@dataclass(frozen=True)
class ToleranceSpec:
    nominal: Decimal
    lower_tol: Decimal | None
    upper_tol: Decimal | None


def _sample_stdev(values: list[Decimal]) -> Decimal:
    mean = sum(values, start=Decimal(0)) / len(values)
    variance = sum(((v - mean) ** 2 for v in values), start=Decimal(0)) / (len(values) - 1)
    return variance.sqrt()


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, start=Decimal(0)) / len(values)


def cp(values: list[Decimal], spec: ToleranceSpec) -> Decimal:
    """Cp = (USL - LSL) / (6 * sample stdev). Requires a bilateral tolerance."""
    if spec.lower_tol is None or spec.upper_tol is None:
        raise ValueError("Cp is undefined for a unilateral tolerance -- use cpk() instead.")
    if len(values) < 2:
        raise ValueError("Cp requires at least 2 values to estimate a standard deviation.")
    stdev = _sample_stdev(values)
    if stdev == 0:
        raise ValueError("Cp is undefined when the sample standard deviation is zero.")
    usl = spec.nominal + spec.upper_tol
    lsl = spec.nominal + spec.lower_tol
    return (usl - lsl) / (6 * stdev)


def cpk(values: list[Decimal], spec: ToleranceSpec) -> Decimal:
    """Cpk = min over present tolerance sides of (limit - mean)/(3*stdev),
    signed so it faces the mean (upper side: USL - mean; lower side:
    mean - LSL). Handles a unilateral spec by only considering the present
    side."""
    if len(values) < 2:
        raise ValueError("Cpk requires at least 2 values to estimate a standard deviation.")
    stdev = _sample_stdev(values)
    if stdev == 0:
        raise ValueError("Cpk is undefined when the sample standard deviation is zero.")
    mean = _mean(values)

    candidates: list[Decimal] = []
    if spec.upper_tol is not None:
        usl = spec.nominal + spec.upper_tol
        candidates.append((usl - mean) / (3 * stdev))
    if spec.lower_tol is not None:
        lsl = spec.nominal + spec.lower_tol
        candidates.append((mean - lsl) / (3 * stdev))

    return min(candidates)
