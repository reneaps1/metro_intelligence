"""F10.D (MI-47): adaptive inspection engine unit tests.

CLAUDE.md §2/§24: the most important property of this module is that it
never produces anything but a *pending candidate* -- these tests exist
specifically to catch a violation of that rule, not just to check the
five recommendation-type branches.
"""

from __future__ import annotations

import dataclasses
import uuid
from decimal import Decimal

from app.engines.adaptive_inspection.recommend import (
    ENGINE_NAME,
    ENGINE_VERSION,
    RecommendationCandidate,
    RiskSignal,
    recommend,
)

RISK_ASSESSMENT_ID = uuid.uuid4()
CHARACTERISTIC_ID = uuid.uuid4()
RESULT_ID = uuid.uuid4()


def _base_signal(**overrides: object) -> RiskSignal:
    defaults: dict[str, object] = dict(
        risk_assessment_id=RISK_ASSESSMENT_ID,
        characteristic_id=CHARACTERISTIC_ID,
        score=10,
        level="low",
        cpk=Decimal("2.0"),
        recent_nok_count=0,
        recent_result_count=30,
        triggering_result_ids=[RESULT_ID],
    )
    defaults.update(overrides)
    return RiskSignal(**defaults)  # type: ignore[arg-type]


def test_candidate_never_carries_a_state_or_operational_field() -> None:
    """Structural guard (CLAUDE.md §2): the type itself must not have a
    `state`, `decided_by`, or frequency-value field -- there is no field to
    accidentally set to 'accepted' or write to catalog_inspection_frequencies."""
    field_names = {f.name for f in dataclasses.fields(RecommendationCandidate)}
    assert field_names == {"recommendation_type", "rationale", "evidence", "engine_name", "engine_version"}
    assert "state" not in field_names
    assert "frequency_value" not in field_names


def test_unvalidated_recent_event_wins_over_everything_else() -> None:
    # Even with a high score and a NOK present, an unvalidated recent event
    # takes priority (§Contexto priority order).
    signal = _base_signal(
        score=90,
        level="critical",
        recent_nok_count=2,
        recent_event_id=uuid.uuid4(),
        recent_event_type="tool_change",
    )
    result = recommend(signal)
    assert result is not None
    assert result.recommendation_type == "post_event_validation"
    assert "tool change" in result.rationale.lower()
    assert result.evidence["event_id"] == str(signal.recent_event_id)


def test_recent_nok_triggers_immediate_inspection() -> None:
    signal = _base_signal(score=45, level="medium", recent_nok_count=1, recent_result_count=12)
    result = recommend(signal)
    assert result is not None
    assert result.recommendation_type == "immediate_inspection"
    assert "1 out-of-tolerance" in result.rationale
    assert "12 measurements" in result.rationale


def test_high_risk_without_nok_triggers_investigate_cause() -> None:
    signal = _base_signal(score=65, level="high", recent_nok_count=0, cpk=Decimal("1.1"))
    result = recommend(signal)
    assert result is not None
    assert result.recommendation_type == "investigate_cause"
    assert "65/100" in result.rationale
    assert "high" in result.rationale.lower()


def test_stable_capable_process_with_enough_history_triggers_frequency_decrease() -> None:
    signal = _base_signal(score=5, level="low", cpk=Decimal("2.0"), recent_result_count=25)
    result = recommend(signal)
    assert result is not None
    assert result.recommendation_type == "frequency_decrease"
    assert "2.0" in result.rationale
    assert "25 measurements" in result.rationale


def test_low_score_but_thin_history_does_not_trigger_frequency_decrease() -> None:
    """A conservative safety rail: even a great-looking score should never
    recommend *less* inspection from a handful of data points."""
    signal = _base_signal(score=5, level="low", cpk=Decimal("2.0"), recent_result_count=5)
    assert recommend(signal) is None


def test_marginal_capability_triggers_frequency_increase() -> None:
    signal = _base_signal(score=45, level="medium", cpk=Decimal("0.8"), recent_result_count=25)
    result = recommend(signal)
    assert result is not None
    assert result.recommendation_type == "frequency_increase"
    assert "0.8" in result.rationale


def test_medium_risk_with_acceptable_cpk_produces_no_recommendation() -> None:
    signal = _base_signal(score=40, level="medium", cpk=Decimal("1.2"), recent_result_count=25)
    assert recommend(signal) is None


def test_rationale_is_never_just_the_bare_score() -> None:
    """CLAUDE.md-derived acceptance criterion: rationale must be readable by
    a non-technical human, not just 'score=87'."""
    signal = _base_signal(score=87, level="critical", cpk=Decimal("0.5"))
    result = recommend(signal)
    assert result is not None
    assert result.rationale != f"score={signal.score}"
    assert len(result.rationale) > len(f"score={signal.score}")


def test_evidence_references_real_ids_not_generic_text() -> None:
    signal = _base_signal(score=65, level="high", cpk=Decimal("1.1"))
    result = recommend(signal)
    assert result is not None
    assert result.evidence["risk_assessment_id"] == str(RISK_ASSESSMENT_ID)
    assert result.evidence["characteristic_id"] == str(CHARACTERISTIC_ID)
    assert result.evidence["triggering_result_ids"] == [str(RESULT_ID)]


def test_candidate_carries_engine_name_and_version() -> None:
    signal = _base_signal(score=65, level="high", cpk=Decimal("1.1"))
    result = recommend(signal)
    assert result is not None
    assert result.engine_name == ENGINE_NAME == "adaptive_inspection_engine"
    assert result.engine_version == ENGINE_VERSION == "v1"
