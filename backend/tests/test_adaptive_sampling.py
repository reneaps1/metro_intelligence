"""EXPERIMENTAL: pure-function vectors (CLAUDE.md §11) for
``app.engines.adaptive_sampling``. No DB -- see
``test_adaptive_sampling_service.py`` for the mocked orchestration tests and
``test_measurements_api.py`` for the real-Postgres endpoint wiring."""

from __future__ import annotations

import random
import uuid
from decimal import Decimal

import pytest
from app.engines.adaptive_sampling import (
    AdaptiveSamplingConfig,
    ExistingRecommendationSignal,
    classify_cpk_trend,
    detect_conflicts,
    recommend_sampling_frequency,
)

# --- recommend_sampling_frequency -------------------------------------------


def test_recommend_returns_conservative_default_for_empty_input() -> None:
    result = recommend_sampling_frequency([])
    assert result.recommended_frequency == 5
    assert result.confidence == 0.0
    assert result.windows_analyzed == 0
    assert result.beta_sample is None


def test_recommend_returns_conservative_default_when_fewer_than_minimum_windows() -> None:
    values = [Decimal("2.0"), Decimal("2.0"), Decimal("2.0")]  # 3 < default minimum of 5
    result = recommend_sampling_frequency(values)
    assert result.recommended_frequency == 5
    assert result.confidence == 0.0
    assert result.windows_analyzed == 3
    assert result.beta_sample is None


def test_recommend_filters_out_none_values_before_counting_windows() -> None:
    values: list[Decimal | None] = [Decimal("2.0")] * 5 + [None, None]
    result = recommend_sampling_frequency(values, rng=random.Random(42))
    assert result.windows_analyzed == 5


def test_recommend_caps_analysis_to_lookback_windows() -> None:
    values = [Decimal("2.0")] * 30
    result = recommend_sampling_frequency(values, rng=random.Random(42))
    assert result.windows_analyzed == 20  # DEFAULT_LOOKBACK_WINDOWS


def test_recommend_is_deterministic_with_a_seeded_rng() -> None:
    values = [Decimal("2.0")] * 6 + [Decimal("1.0")] * 4
    first = recommend_sampling_frequency(values, rng=random.Random(42))
    second = recommend_sampling_frequency(values, rng=random.Random(42))
    assert first.recommended_frequency == second.recommended_frequency
    assert first.confidence == second.confidence
    assert first.beta_sample == second.beta_sample


def test_recommend_recommends_sparsest_bucket_for_all_capable_windows() -> None:
    values = [Decimal("2.0")] * 10  # all above the 1.67 threshold
    result = recommend_sampling_frequency(values, rng=random.Random(42))
    assert result.successes == 10
    assert result.failures == 0
    assert result.recommended_frequency == 100
    assert result.confidence > 0.9


def test_recommend_recommends_tightest_bucket_for_all_unstable_windows() -> None:
    values = [Decimal("1.0")] * 10  # all at/below the 1.67 threshold
    result = recommend_sampling_frequency(values, rng=random.Random(42))
    assert result.successes == 0
    assert result.failures == 10
    assert result.recommended_frequency == 5
    assert result.confidence > 0.9


def test_recommend_recommends_an_intermediate_frequency_for_mixed_cpk() -> None:
    values = [Decimal("2.0")] * 5 + [Decimal("1.0")] * 5
    result = recommend_sampling_frequency(values, rng=random.Random(42))
    assert result.successes == 5
    assert result.failures == 5
    assert 5 < result.recommended_frequency < 100


@pytest.mark.parametrize("successes", [0, 3, 5, 7, 10])
def test_recommend_frequency_always_within_configured_bounds(successes: int) -> None:
    values = [Decimal("2.0")] * successes + [Decimal("1.0")] * (10 - successes)
    for seed in range(5):
        result = recommend_sampling_frequency(values, rng=random.Random(seed))
        assert 5 <= result.recommended_frequency <= 100
        assert 0.0 <= result.confidence <= 1.0


def test_recommend_clamps_a_custom_bucket_above_maximum_frequency() -> None:
    config = AdaptiveSamplingConfig(frequency_buckets=(5, 10, 20, 50, 200), maximum_frequency=100)
    values = [Decimal("2.0")] * 10
    result = recommend_sampling_frequency(values, config=config, rng=random.Random(42))
    assert result.recommended_frequency == 100  # clamped down from the 200 bucket


def test_recommend_rationale_mentions_thompson_sampling_and_engine_attribution() -> None:
    values = [Decimal("2.0")] * 10
    result = recommend_sampling_frequency(values, rng=random.Random(42))
    assert "Thompson Sampling" in result.rationale
    assert result.engine_name == "adaptive_sampling_engine"
    assert result.engine_version == "v1-experimental"


# --- classify_cpk_trend -------------------------------------------------------


def test_classify_cpk_trend_returns_stable_for_fewer_than_two_values() -> None:
    assert classify_cpk_trend([]) == "stable"
    assert classify_cpk_trend([Decimal("1.8")]) == "stable"


def test_classify_cpk_trend_returns_stable_within_tolerance_band() -> None:
    values = [Decimal("1.50"), Decimal("1.52"), Decimal("1.55"), Decimal("1.58")]
    assert classify_cpk_trend(values, tolerance=0.1) == "stable"


def test_classify_cpk_trend_returns_improving_beyond_tolerance() -> None:
    values = [Decimal("1.20"), Decimal("1.25"), Decimal("1.80"), Decimal("1.90")]
    assert classify_cpk_trend(values, tolerance=0.1) == "improving"


def test_classify_cpk_trend_returns_declining_beyond_tolerance() -> None:
    values = [Decimal("1.90"), Decimal("1.80"), Decimal("1.25"), Decimal("1.20")]
    assert classify_cpk_trend(values, tolerance=0.1) == "declining"


# --- detect_conflicts ---------------------------------------------------------


def _signal(
    recommendation_type: str, state: str, rationale: str = "Example rationale."
) -> ExistingRecommendationSignal:
    return ExistingRecommendationSignal(
        id=uuid.uuid4(), recommendation_type=recommendation_type, state=state, rationale=rationale
    )


def test_detect_conflicts_pending_frequency_increase_conflicts() -> None:
    conflicts = detect_conflicts([_signal("frequency_increase", "pending")], recommended_frequency=100)
    assert len(conflicts) == 1
    assert conflicts[0].type == "frequency_increase"
    assert conflicts[0].status == "pending"


def test_detect_conflicts_pending_immediate_inspection_conflicts() -> None:
    conflicts = detect_conflicts([_signal("immediate_inspection", "pending")], recommended_frequency=100)
    assert len(conflicts) == 1


def test_detect_conflicts_pending_investigate_cause_conflicts() -> None:
    conflicts = detect_conflicts([_signal("investigate_cause", "pending")], recommended_frequency=100)
    assert len(conflicts) == 1


def test_detect_conflicts_accepted_tightening_type_uses_stronger_wording_than_pending() -> None:
    pending = detect_conflicts([_signal("frequency_increase", "pending")], recommended_frequency=100)
    accepted = detect_conflicts([_signal("frequency_increase", "accepted")], recommended_frequency=100)
    assert "already-accepted" in accepted[0].conflict_reason
    assert "already-accepted" not in pending[0].conflict_reason


def test_detect_conflicts_pending_frequency_decrease_conflicts_only_at_the_tight_threshold() -> None:
    tight = detect_conflicts([_signal("frequency_decrease", "pending")], recommended_frequency=5)
    sparse = detect_conflicts([_signal("frequency_decrease", "pending")], recommended_frequency=100)
    assert len(tight) == 1
    assert sparse == []


def test_detect_conflicts_rejected_never_conflicts() -> None:
    conflicts = detect_conflicts([_signal("frequency_increase", "rejected")], recommended_frequency=100)
    assert conflicts == []


def test_detect_conflicts_superseded_and_expired_never_conflict() -> None:
    conflicts = detect_conflicts(
        [_signal("frequency_increase", "superseded"), _signal("frequency_increase", "expired")],
        recommended_frequency=100,
    )
    assert conflicts == []


def test_detect_conflicts_post_event_validation_is_never_auto_flagged() -> None:
    conflicts = detect_conflicts([_signal("post_event_validation", "pending")], recommended_frequency=100)
    assert conflicts == []


def test_detect_conflicts_unknown_future_type_is_never_auto_flagged() -> None:
    conflicts = detect_conflicts([_signal("something_new", "pending")], recommended_frequency=100)
    assert conflicts == []


def test_detect_conflicts_entries_have_no_severity_key() -> None:
    conflicts = detect_conflicts([_signal("frequency_increase", "pending")], recommended_frequency=100)
    entry = {
        "id": str(conflicts[0].id),
        "type": conflicts[0].type,
        "status": conflicts[0].status,
        "title": conflicts[0].title,
        "reason": conflicts[0].reason,
        "conflict_reason": conflicts[0].conflict_reason,
    }
    assert set(entry.keys()) == {"id", "type", "status", "title", "reason", "conflict_reason"}
    assert "severity" not in entry


def test_detect_conflicts_title_truncates_long_rationale() -> None:
    long_rationale = "x" * 200
    conflicts = detect_conflicts(
        [_signal("frequency_increase", "pending", rationale=long_rationale)], recommended_frequency=100
    )
    assert len(conflicts[0].title) < len(long_rationale)
    assert conflicts[0].title.endswith("...")


def test_detect_conflicts_multiple_existing_recommendations_handled_without_duplicates() -> None:
    conflicts = detect_conflicts(
        [
            _signal("frequency_increase", "pending"),
            _signal("frequency_decrease", "pending"),
            _signal("post_event_validation", "pending"),
            _signal("frequency_increase", "rejected"),
        ],
        recommended_frequency=100,
    )
    ids = [c.id for c in conflicts]
    assert len(ids) == len(set(ids))
    assert len(conflicts) == 1  # only the pending frequency_increase conflicts at frequency=100
