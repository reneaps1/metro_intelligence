"""IQ-F7: HYPOTHETICAL what-if over the Vista B synthetic mechanism.

Answers "what would happen to the synthetic pin length if hold pressure or
mold temperature changed?" by evaluating the exact formula the simulator uses
(`generator.py`, README "Vista B"), never a fitted model:

    length = 12.000 + 0.006·Δmold_temp − 0.0006·(hold_pressure − 620)
             + nest offset (+ worn insert) + noise

P(NOK) is the normal tail outside ±0.050 mm, with the per-piece spread made
of the measurement noise and the cycle-to-cycle hold-pressure scatter. The
mechanism is IMPOSED on purpose: the result says what the simulator would do,
not what a real press would do. Cycle time does not appear in the mechanism,
so it is not offered as a lever (stated, not faked).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.engines.process_simulation.catalog import MACHINES
from app.engines.process_simulation.generator import (
    DIM_HOLD_COEF_MM_PER_BAR,
    DIM_MOLD_COEF_MM_PER_C,
    DIM_NOISE_MM,
    DIM_NOMINAL_MM,
    DIM_TOL_MM,
    HOLD_NOISE_BAR,
    HOLD_REFERENCE_BAR,
    NEST_COUNT,
    nest_offsets,
)
from app.engines.process_simulation.scenarios import get_scenario

HOLD_RANGE_BAR = (540.0, 700.0)
MOLD_DELTA_RANGE_C = (-5.0, 15.0)
_WORN = get_scenario("intermittent_fault_cavity_change").worn_nest
WORN_NEST = _WORN[0] if _WORN else 7
WORN_OFFSET_MM = _WORN[1] if _WORN else 0.04
PIECE_SD_MM = math.hypot(DIM_NOISE_MM, DIM_HOLD_COEF_MM_PER_BAR * HOLD_NOISE_BAR)
PRIMARY_MACHINE = next(m.code for m in MACHINES if m.primary)


@dataclass(frozen=True)
class Contribution:
    label: str
    mm: float


@dataclass(frozen=True)
class SweepPoint:
    x: float
    nok_probability: float


@dataclass(frozen=True)
class WhatIfResult:
    hold_pressure_bar: float
    mold_delta_c: float
    nest: int | None
    worn_insert: bool
    nominal_mm: float
    tolerance_mm: float
    mean_mm: float
    piece_sd_mm: float
    nok_probability: float
    reference_nok_probability: float
    contributions: list[Contribution]
    hold_sweep: list[SweepPoint]
    mold_sweep: list[SweepPoint]


def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def nok_probability_normal(mean: float, sd: float) -> float:
    """P(|x − nominal| > tol) for x ~ N(mean, sd)."""
    low = (DIM_NOMINAL_MM - DIM_TOL_MM - mean) / sd
    high = (DIM_NOMINAL_MM + DIM_TOL_MM - mean) / sd
    return _phi(low) + (1.0 - _phi(high))


def _nest_shift(nest: int, worn_insert: bool, offsets: tuple[float, ...]) -> float:
    return offsets[nest - 1] + (WORN_OFFSET_MM if worn_insert and nest == WORN_NEST else 0.0)


def _process_shift(hold_pressure: float, mold_delta: float) -> float:
    return DIM_MOLD_COEF_MM_PER_C * mold_delta + DIM_HOLD_COEF_MM_PER_BAR * (
        hold_pressure - HOLD_REFERENCE_BAR
    )


def _probability(hold_pressure: float, mold_delta: float, nest: int | None, worn: bool) -> float:
    offsets = nest_offsets(PRIMARY_MACHINE)
    base = DIM_NOMINAL_MM + _process_shift(hold_pressure, mold_delta)
    nests = [nest] if nest is not None else list(range(1, NEST_COUNT + 1))
    # Every nest gets the same share of shots: P(NOK) is the plain mixture average.
    return sum(
        nok_probability_normal(base + _nest_shift(n, worn, offsets), PIECE_SD_MM) for n in nests
    ) / len(nests)


def what_if(
    hold_pressure: float, mold_delta: float, nest: int | None = None, worn_insert: bool = False
) -> WhatIfResult:
    """Evaluate the synthetic mechanism. ``nest=None`` averages all nests."""
    if not HOLD_RANGE_BAR[0] <= hold_pressure <= HOLD_RANGE_BAR[1]:
        raise ValueError("hold pressure out of range")
    if not MOLD_DELTA_RANGE_C[0] <= mold_delta <= MOLD_DELTA_RANGE_C[1]:
        raise ValueError("mold temperature delta out of range")
    if nest is not None and not 1 <= nest <= NEST_COUNT:
        raise ValueError("nest out of range")
    offsets = nest_offsets(PRIMARY_MACHINE)
    nests = [nest] if nest is not None else list(range(1, NEST_COUNT + 1))
    nest_part = sum(_nest_shift(n, False, offsets) for n in nests) / len(nests)
    worn_part = (
        (WORN_OFFSET_MM / (1 if nest is not None else NEST_COUNT))
        if worn_insert and (nest is None or nest == WORN_NEST)
        else 0.0
    )
    contributions = [
        Contribution("Temperatura de molde (Δ)", DIM_MOLD_COEF_MM_PER_C * mold_delta),
        Contribution(
            "Presión de mantenimiento", DIM_HOLD_COEF_MM_PER_BAR * (hold_pressure - HOLD_REFERENCE_BAR)
        ),
        Contribution("Nido" if nest is not None else "Nidos (promedio)", nest_part),
        Contribution(f"Inserto desgastado (nido {WORN_NEST})", worn_part),
    ]
    steps_hold = int((HOLD_RANGE_BAR[1] - HOLD_RANGE_BAR[0]) / 10)
    steps_mold = int(MOLD_DELTA_RANGE_C[1] - MOLD_DELTA_RANGE_C[0])
    return WhatIfResult(
        hold_pressure_bar=hold_pressure,
        mold_delta_c=mold_delta,
        nest=nest,
        worn_insert=worn_insert,
        nominal_mm=DIM_NOMINAL_MM,
        tolerance_mm=DIM_TOL_MM,
        mean_mm=DIM_NOMINAL_MM + sum(c.mm for c in contributions),
        piece_sd_mm=PIECE_SD_MM,
        nok_probability=_probability(hold_pressure, mold_delta, nest, worn_insert),
        reference_nok_probability=_probability(HOLD_REFERENCE_BAR, 0.0, nest, False),
        contributions=contributions,
        hold_sweep=[
            SweepPoint(x, _probability(x, mold_delta, nest, worn_insert))
            for x in (HOLD_RANGE_BAR[0] + 10 * i for i in range(steps_hold + 1))
        ],
        mold_sweep=[
            SweepPoint(x, _probability(hold_pressure, x, nest, worn_insert))
            for x in (MOLD_DELTA_RANGE_C[0] + i for i in range(steps_mold + 1))
        ],
    )
