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
