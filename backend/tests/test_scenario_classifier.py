"""LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): unit tests for
the pure scenario-scoring core (`compute_profile`/`rank_by_scenario`). No
database -- `load_candidate_profiles`'s DB-backed loading is exercised in
``test_live_monitor_api.py`` against a real Postgres instance.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.models.catalog import Specification
from app.services.scenario_classifier import SCENARIO_NAMES, compute_profile, rank_by_scenario

STABLE_VALUES = [Decimal(v) for v in ("10.00", "10.01", "9.99", "10.00", "10.01", "9.99")]
NOISY_VALUES = [Decimal(v) for v in ("10.0", "10.8", "9.2", "10.7", "9.3", "10.0")]
DRIFTING_VALUES = [Decimal(v) for v in ("10.00", "10.05", "10.10", "10.20", "10.35", "10.50")]
STEPPED_VALUES = [Decimal(v) for v in ("10.00", "10.01", "9.99", "10.60", "10.61", "10.59")]
ALL_OK = [True] * 6


def _spec(**overrides: object) -> Specification:
    defaults: dict[str, object] = {
        "nominal": Decimal("10"),
        "lower_tol": Decimal("-1"),
        "upper_tol": Decimal("1"),
        "unit": "mm",
    }
    defaults.update(overrides)
    return Specification(**defaults)  # type: ignore[arg-type]


def test_all_five_seed_scenarios_have_a_scorer() -> None:
    # scenarios.yaml's exact 5 keys -- LM.3 scope forbids inventing new ones.
    assert set(SCENARIO_NAMES) == {
        "stable_capable",
        "slow_drift",
        "shift_after_event",
        "high_variance",
        "outlier_nok",
    }


def test_stable_low_variance_run_ranks_highest_for_stable_capable() -> None:
    spec = _spec()
    stable = compute_profile(uuid.uuid4(), STABLE_VALUES, ALL_OK, spec)
    noisy = compute_profile(uuid.uuid4(), NOISY_VALUES, ALL_OK, spec)

    winner = rank_by_scenario([stable, noisy], "stable_capable", limit=1)
    assert winner == [stable.characteristic_id]


def test_high_variance_run_ranks_above_a_stable_one() -> None:
    spec = _spec()
    stable = compute_profile(uuid.uuid4(), STABLE_VALUES, ALL_OK, spec)
    noisy = compute_profile(uuid.uuid4(), NOISY_VALUES, ALL_OK, spec)

    winner = rank_by_scenario([stable, noisy], "high_variance", limit=1)
    assert winner == [noisy.characteristic_id]


def test_gradual_drift_ranks_above_stable_for_slow_drift() -> None:
    spec = _spec()
    drifting = compute_profile(uuid.uuid4(), DRIFTING_VALUES, ALL_OK, spec)
    stable = compute_profile(uuid.uuid4(), STABLE_VALUES, ALL_OK, spec)

    winner = rank_by_scenario([drifting, stable], "slow_drift", limit=1)
    assert winner == [drifting.characteristic_id]


def test_sudden_step_ranks_above_gradual_drift_for_shift_after_event() -> None:
    spec = _spec()
    # A flat run that jumps sharply halfway through -- a step, not a
    # gradual trend across the whole window.
    stepped = compute_profile(uuid.uuid4(), STEPPED_VALUES, ALL_OK, spec)
    drifting = compute_profile(uuid.uuid4(), DRIFTING_VALUES, ALL_OK, spec)

    winner = rank_by_scenario([stepped, drifting], "shift_after_event", limit=1)
    assert winner == [stepped.characteristic_id]


def test_elevated_nok_rate_ranks_highest_for_outlier_nok() -> None:
    spec = _spec()
    outlier_values = [Decimal(v) for v in ("10.0", "10.0", "9.9", "12.5", "10.0", "10.1")]
    outlier_flags = [True, True, True, False, True, True]
    with_outliers = compute_profile(uuid.uuid4(), outlier_values, outlier_flags, spec)
    clean = compute_profile(uuid.uuid4(), STABLE_VALUES, ALL_OK, spec)

    winner = rank_by_scenario([with_outliers, clean], "outlier_nok", limit=1)
    assert winner == [with_outliers.characteristic_id]


def test_unevaluated_result_counts_toward_nok_rate_defensively() -> None:
    spec = _spec()
    values = [Decimal(v) for v in ("10.0", "10.0", "10.0", "10.0")]
    profile = compute_profile(uuid.uuid4(), values, [True, None, True, True], spec)
    assert profile.nok_rate == Decimal("1") / Decimal("4")


def test_rank_by_scenario_returns_at_most_limit_ids() -> None:
    spec = _spec()
    values = [Decimal("10.0"), Decimal("10.1"), Decimal("9.9")]
    profiles = [compute_profile(uuid.uuid4(), values, [True] * 3, spec) for _ in range(5)]
    assert len(rank_by_scenario(profiles, "stable_capable", limit=2)) == 2


def test_zero_variance_run_yields_a_defined_score_not_a_crash() -> None:
    # cpk() raises ValueError for zero variance -- compute_profile must catch
    # that and report cpk=None rather than propagating.
    profile = compute_profile(uuid.uuid4(), [Decimal("10.0")] * 6, ALL_OK, _spec())
    assert profile.cpk is None
    # Still rankable -- doesn't raise when scored.
    assert rank_by_scenario([profile], "stable_capable", limit=1) == [profile.characteristic_id]
