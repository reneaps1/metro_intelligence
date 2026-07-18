"""Live Monitor alarm fix (2026-07): rule-based, explainable alarm detection
over the real Compliance/SPC engine output the live replay already computes.

Pure engine functions (CLAUDE.md §3): no DB access, no I/O. Deliberately
takes plain values rather than importing
`app.services.live_replay_service`'s `PointEvent`/`ControlLimitsEvent` --
engines don't depend on services (the dependency runs the other way), same
as `capability.py`/`control_limits.py` in this package.

Two rules, both a direct read of an already-computed real value -- no
forecasting, no invented confidence number (CLAUDE.md §16, §22; see
`docs/design/live-monitor-panel.md` lines 16-22 for why this project never
frames a rule as "the model predicts"):

- `evaluate_compliance_alarm`: the real Compliance engine (F7.D) already
  marked this point `is_ok=False`.
- `evaluate_capability_alarm`: the real SPC engine (F8.D) already computed a
  Cpk below the standard 1.33 capability threshold for the latest window.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

ENGINE_NAME = "alarm_rules_engine"
ENGINE_VERSION = "v1"

# Same standard SPC "capable" convention already used to phrase Cpk in
# `SignalDetailPanel`/`LiveMonitorDetailPage` on the frontend -- never a
# second, different number invented here.
CPK_CAPABLE_THRESHOLD = Decimal("1.33")
# Below this, a capability alarm is "critical" rather than "warning" -- not a
# standard SPC constant like 1.33 itself, a deliberate, documented choice for
# this alarm rule: well below capable, not just marginal.
CPK_CRITICAL_THRESHOLD = Decimal("1.0")


@dataclass(frozen=True)
class AlarmRuleResult:
    trigger_type: str
    severity: str
    rationale: str
    computed_inputs: dict[str, Any]
    engine_name: str = ENGINE_NAME
    engine_version: str = ENGINE_VERSION


def evaluate_compliance_alarm(
    *, is_ok: bool, rationale: str, value: Decimal, deviation: Decimal
) -> AlarmRuleResult | None:
    """`None` when the point is OK -- nothing to alarm on."""
    if is_ok:
        return None
    return AlarmRuleResult(
        trigger_type="compliance_violation",
        severity="warning",
        rationale=rationale,
        computed_inputs={"value": str(value), "deviation": str(deviation)},
    )


def evaluate_capability_alarm(
    *,
    cpk: Decimal | None,
    ucl: Decimal,
    lcl: Decimal,
    threshold: Decimal = CPK_CAPABLE_THRESHOLD,
) -> AlarmRuleResult | None:
    """`None` when Cpk is undefined (zero-variance run so far, or a
    unilateral spec) or still at/above the threshold -- nothing to alarm on."""
    if cpk is None or cpk >= threshold:
        return None
    severity = "critical" if cpk < CPK_CRITICAL_THRESHOLD else "warning"
    rationale = f"Cpk {cpk} -- below the {threshold} capability threshold ({ENGINE_NAME} {ENGINE_VERSION})."
    return AlarmRuleResult(
        trigger_type="capability_below_threshold",
        severity=severity,
        rationale=rationale,
        computed_inputs={"cpk": str(cpk), "ucl": str(ucl), "lcl": str(lcl), "threshold": str(threshold)},
    )
