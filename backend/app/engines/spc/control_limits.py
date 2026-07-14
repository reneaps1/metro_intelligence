"""F8.D (MI-45): I-MR (Individuals & Moving Range) control limits.

Pure engine function (CLAUDE.md §3): no DB access. Individuals charts
(subgroup size 1, moving range from consecutive pairs, so n=2 for the
tabulated constants below) use standard, textbook control-chart constants --
these are looked up, not derived or estimated:

- D2 = 1.128: bias-correction factor so mean(moving range)/D2 estimates
  sigma for an individuals chart.
- D3 = 0, D4 = 3.267: moving-range chart limits (LCL/UCL) for n=2.
- E2 = 2.660 (= 3/D2): individuals-chart limit multiplier for n=2.

Source: Montgomery, "Introduction to Statistical Quality Control", control
chart constants table (subgroup size 2). Full Nelson/Western Electric
pattern-detection rules are out of scope for this task (docs/tasks/F8.D.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ENGINE_NAME = "spc_engine"
ENGINE_VERSION = "v1"

D2 = Decimal("1.128")
D3 = Decimal("0")
D4 = Decimal("3.267")
E2 = Decimal("2.660")


@dataclass(frozen=True)
class ControlLimits:
    center_line: Decimal
    individuals_ucl: Decimal
    individuals_lcl: Decimal
    mr_center_line: Decimal
    mr_ucl: Decimal
    mr_lcl: Decimal
    engine_name: str
    engine_version: str


def individuals_moving_range_limits(values: list[Decimal]) -> ControlLimits:
    if len(values) < 2:
        raise ValueError("I-MR control limits require at least 2 values to compute a moving range.")

    moving_ranges = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mean = sum(values, start=Decimal(0)) / len(values)
    mr_bar = sum(moving_ranges, start=Decimal(0)) / len(moving_ranges)

    return ControlLimits(
        center_line=mean,
        individuals_ucl=mean + E2 * mr_bar,
        individuals_lcl=mean - E2 * mr_bar,
        mr_center_line=mr_bar,
        mr_ucl=D4 * mr_bar,
        mr_lcl=max(D3 * mr_bar, Decimal(0)),
        engine_name=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
    )
