"""One rule for the status of a process step (ADR-005).

Thresholds are product decisions and live here only; the owner may tune
them. Steps with a specification use the drawing verdict; steps without one
(electrical tests, type check) fall back to the station's own verdict.
"""

from __future__ import annotations

from typing import Literal

Status = Literal["ok", "warning", "critical", "neutral"]

CRITICAL_NOK_RATE = 0.01  # 1 % of pieces out of tolerance
CAPABLE_CPK = 1.33
MIN_CPK = 1.0
# A step that logs fewer than half of the pieces seen at type check keeps a
# partial record (electrical tests log a sample; a station may be partly
# loaded). Its rates describe that sample, not the line.
PARTIAL_COVERAGE = 0.5


def is_partial(coverage: float | None) -> bool:
    """True when a step recorded under half of the line's reference pieces."""
    return coverage is not None and coverage < PARTIAL_COVERAGE


def rolled_yield(nok_rates: list[float]) -> float | None:
    """Share of pieces expected to pass every step: the product of each
    step's pass rate. None without steps."""
    if not nok_rates:
        return None
    result = 1.0
    for rate in nok_rates:
        result *= 1.0 - rate
    return result


def step_status(pieces: int, nok_rate: float | None, worst_cpk: float | None) -> Status:
    """critical: NOK rate >= 1 % or Cpk < 1.0; warning: any NOK or
    Cpk < 1.33; ok otherwise; neutral without pieces."""
    if pieces == 0 or nok_rate is None:
        return "neutral"
    if nok_rate >= CRITICAL_NOK_RATE or (worst_cpk is not None and worst_cpk < MIN_CPK):
        return "critical"
    if nok_rate > 0 or (worst_cpk is not None and worst_cpk < CAPABLE_CPK):
        return "warning"
    return "ok"
