"""Live Monitor alarm fix: pure rule-function vectors (CLAUDE.md §11) for
``app.engines.spc.alarm_rules``. No DB, no I/O -- see
``test_alarm_detection_service.py`` for persistence and
``test_live_monitor_api.py`` for the WS wiring."""

from __future__ import annotations

from decimal import Decimal

from app.engines.spc.alarm_rules import (
    CPK_CAPABLE_THRESHOLD,
    CPK_CRITICAL_THRESHOLD,
    evaluate_capability_alarm,
    evaluate_compliance_alarm,
)


def test_compliance_alarm_is_none_for_an_ok_point() -> None:
    result = evaluate_compliance_alarm(
        is_ok=True, rationale="Within tolerance.", value=Decimal("10.01"), deviation=Decimal("0.01")
    )
    assert result is None


def test_compliance_alarm_fires_for_a_nok_point_with_the_real_rationale() -> None:
    result = evaluate_compliance_alarm(
        is_ok=False,
        rationale="0.150 mm above the upper tolerance limit.",
        value=Decimal("10.15"),
        deviation=Decimal("0.15"),
    )
    assert result is not None
    assert result.trigger_type == "compliance_violation"
    assert result.severity == "warning"
    assert result.rationale == "0.150 mm above the upper tolerance limit."
    assert result.computed_inputs == {"value": "10.15", "deviation": "0.15"}


def test_capability_alarm_is_none_when_cpk_is_undefined() -> None:
    result = evaluate_capability_alarm(cpk=None, ucl=Decimal("10.1"), lcl=Decimal("9.9"))
    assert result is None


def test_capability_alarm_is_none_at_or_above_the_threshold() -> None:
    assert evaluate_capability_alarm(cpk=CPK_CAPABLE_THRESHOLD, ucl=Decimal("1"), lcl=Decimal("0")) is None
    assert evaluate_capability_alarm(cpk=Decimal("1.80"), ucl=Decimal("1"), lcl=Decimal("0")) is None


def test_capability_alarm_is_a_warning_between_critical_and_capable() -> None:
    result = evaluate_capability_alarm(cpk=Decimal("1.20"), ucl=Decimal("10.1"), lcl=Decimal("9.9"))
    assert result is not None
    assert result.trigger_type == "capability_below_threshold"
    assert result.severity == "warning"
    assert "1.20" in result.rationale
    assert "1.33" in result.rationale
    assert result.computed_inputs == {"cpk": "1.20", "ucl": "10.1", "lcl": "9.9", "threshold": "1.33"}


def test_capability_alarm_is_critical_well_below_threshold() -> None:
    result = evaluate_capability_alarm(cpk=Decimal("0.80"), ucl=Decimal("10.1"), lcl=Decimal("9.9"))
    assert result is not None
    assert result.severity == "critical"


def test_capability_alarm_severity_boundary_is_exclusive_of_critical_threshold() -> None:
    # Exactly at CPK_CRITICAL_THRESHOLD (1.0) is still "warning", not
    # "critical" -- the rule is strictly less-than.
    result = evaluate_capability_alarm(cpk=CPK_CRITICAL_THRESHOLD, ucl=Decimal("1"), lcl=Decimal("0"))
    assert result is not None
    assert result.severity == "warning"


def test_every_alarm_carries_real_engine_attribution() -> None:
    result = evaluate_compliance_alarm(
        is_ok=False, rationale="x", value=Decimal("1"), deviation=Decimal("1")
    )
    assert result is not None
    assert result.engine_name == "alarm_rules_engine"
    assert result.engine_version
