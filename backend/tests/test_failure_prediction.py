"""IQ-F7.b: simulated failure history + experimental failure-prediction study.

Pure tests (no database): the engines under test do no IO.
"""

from __future__ import annotations

import math
import time
from dataclasses import replace

import pytest
from app.engines.experimental_ml.failure_prediction import (
    ENGINE_VERSION,
    FEATURES,
    HORIZON_H,
    LogisticModel,
    ThresholdRow,
    average_precision,
    confusion,
    evaluate_episodes,
    features_at,
    fit_logistic,
    predict_proba,
    run_study,
)
from app.engines.process_simulation.failure_history import (
    MACHINES,
    WEEKS,
    FailureEvent,
    simulate_history,
)

# --------------------------------------------------------------------------- simulator


def test_simulator_is_deterministic_and_machines_differ() -> None:
    first = simulate_history("INY-01")
    simulate_history.cache_clear()
    second = simulate_history("INY-01")
    assert first == second
    assert simulate_history("INY-02").vibration != first.vibration


def test_simulator_shapes_and_failure_counts() -> None:
    total_failures = 0
    without_precursor = 0
    for machine in MACHINES:
        history = simulate_history(machine)
        assert history.hours == WEEKS * 168
        assert len(history.vibration) == len(history.current) == history.hours
        assert len(history.alarms) == len(history.downtime) == history.hours
        weekly = len(history.failures) / WEEKS
        assert 0.5 <= weekly <= 4.0
        for event in history.failures:
            assert history.downtime[event.hour + 1]
            assert not history.downtime[event.hour]
            if event.has_precursor:
                assert event.lead_h is not None and 3 <= event.lead_h <= 10
            else:
                assert event.lead_h is None
        total_failures += len(history.failures)
        without_precursor += sum(1 for e in history.failures if not e.has_precursor)
    assert without_precursor > 0
    assert 0.55 <= 1 - without_precursor / total_failures <= 0.85


def test_unknown_machine_rejected() -> None:
    with pytest.raises(ValueError):
        simulate_history("INY-99")


# --------------------------------------------------------------------------- logistic regression


def test_fit_logistic_positive_coefficient_on_separable_ish_data() -> None:
    xs = [-3.0, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 0.2]
    ys = [0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 0]
    model = fit_logistic([[x] for x in xs], ys, l2=1.0)
    assert model.coefficients[0] > 0.5
    assert model.iterations < 30
    assert predict_proba(model, [3.0]) > 0.8 > 0.2 > predict_proba(model, [-3.0])
    flipped = fit_logistic([[-x] for x in xs], ys, l2=1.0)
    assert flipped.coefficients[0] < -0.5


def test_fit_logistic_independent_balanced_gives_zero() -> None:
    xs = [-2.0, -1.0, 0.0, 1.0, 2.0]
    rows = [[x] for x in xs for _ in range(2)]
    ys = [label for _ in xs for label in (0, 1)]
    model = fit_logistic(rows, ys, l2=1.0)
    assert abs(model.coefficients[0]) < 1e-6
    assert abs(model.intercept) < 1e-6


def test_fit_logistic_independent_unbalanced_intercept_is_base_logit() -> None:
    xs = [-2.0, -1.0, 0.0, 1.0, 2.0]
    rows = [[x] for x in xs for _ in range(4)]
    ys = [label for _ in xs for label in (1, 0, 0, 0)]
    model = fit_logistic(rows, ys, l2=1.0)
    assert abs(model.coefficients[0]) < 1e-6
    assert model.intercept == pytest.approx(math.log(0.25 / 0.75), abs=1e-6)


def test_predict_proba_is_numerically_safe() -> None:
    model = LogisticModel(intercept=0.0, coefficients=[1.0], iterations=1)
    assert 0.0 < predict_proba(model, [1e6]) <= 1.0
    assert 0.0 <= predict_proba(model, [-1e6]) < 1.0


# --------------------------------------------------------------------------- leakage


def test_features_use_no_future_data() -> None:
    history = simulate_history("INY-02")
    t = history.failures[3].hour - 2  # just before a failure: its precursor is visible
    keys = {key for key, _ in FEATURES}
    future = range(t + 1, history.hours)
    modified = replace(
        history,
        vibration=[v if h <= t else 99.0 for h, v in enumerate(history.vibration)],
        current=[c if h <= t else -5.0 for h, c in enumerate(history.current)],
        alarms=[a if h <= t else 50 for h, a in enumerate(history.alarms)],
        failures=[e for e in history.failures if e.hour <= t]
        + [FailureEvent(hour=h, has_precursor=False, lead_h=None) for h in future[:3]],
        maintenance_h=[h for h in history.maintenance_h if h <= t] + [t + 1],
        downtime=[d if h <= t else True for h, d in enumerate(history.downtime)],
    )
    original = features_at(history, t)
    assert set(original) == keys
    assert features_at(modified, t) == original


# --------------------------------------------------------------------------- evaluation helpers


def test_confusion_hand_vector() -> None:
    scores = [0.9, 0.6, 0.4, 0.2, 0.5]
    labels = [1, 0, 1, 0, 1]
    assert confusion(scores, labels, 0.5) == (2, 1, 1, 1)
    assert confusion(scores, labels, 0.95) == (0, 0, 3, 2)


def test_average_precision_hand_vectors() -> None:
    assert average_precision([0.9, 0.8, 0.3, 0.1], [1, 1, 0, 0]) == pytest.approx(1.0)
    # Ranking 1,0,1,0 -> 0.5 * 1 + 0.5 * (2/3).
    assert average_precision([0.9, 0.8, 0.3, 0.1], [1, 0, 1, 0]) == pytest.approx(0.5 + 1 / 3)
    # All tied -> precision equals the base rate.
    assert average_precision([0.2] * 4, [1, 0, 0, 0]) == pytest.approx(0.25)
    assert average_precision([0.1, 0.2], [0, 0]) == 0.0


def test_evaluate_episodes_lead_and_window() -> None:
    result = evaluate_episodes([95, 96, 97], [100], horizon_h=6)
    assert result.episodes_total == 1
    assert result.episodes_anticipated == 1
    assert result.leads == [5]
    assert result.alert_events == 1
    assert result.false_alarm_events == 0


def test_evaluate_episodes_alert_at_or_after_failure_does_not_count() -> None:
    at_failure = evaluate_episodes([100], [100], horizon_h=6)
    assert at_failure.episodes_anticipated == 0
    after = evaluate_episodes([101, 102], [100], horizon_h=6)
    assert after.episodes_anticipated == 0
    assert after.leads == []
    too_early = evaluate_episodes([90], [100], horizon_h=6)
    assert too_early.episodes_anticipated == 0


def test_evaluate_episodes_false_alarms_and_debounce() -> None:
    result = evaluate_episodes([10, 11, 12, 30, 50, 51, 98, 99], [100], horizon_h=6)
    assert result.alert_events == 4  # runs 10-12, 30, 50-51, 98-99
    assert result.false_alarm_events == 3
    assert result.episodes_anticipated == 1
    assert result.leads == [2]


# --------------------------------------------------------------------------- study


def test_study_is_honest_and_fast() -> None:
    run_study.cache_clear()
    simulate_history.cache_clear()
    started = time.perf_counter()
    study = run_study()
    assert time.perf_counter() - started < 3.0
    assert run_study() is study
    assert study.engine_version == ENGINE_VERSION
    assert study.engine_version.endswith("-experimental")
    assert study.horizon_h == HORIZON_H
    assert study.split.test_failures >= 15

    def rows(row: ThresholdRow) -> int:
        return row.tp + row.fp + row.fn + row.tn

    for threshold_row in study.thresholds:
        assert rows(threshold_row) == study.split.test_rows
    for baseline in study.baselines:
        assert rows(baseline.at_half) == study.split.test_rows
        assert baseline.at_half.episodes_total == study.split.test_failures

    baselines = {b.key: b for b in study.baselines}
    assert set(baselines) == {"last_hour_failure", "constant_rate"}
    assert study.model_pr_auc > baselines["constant_rate"].pr_auc
    assert study.model_pr_auc > baselines["last_hour_failure"].pr_auc
    assert baselines["constant_rate"].at_half.alert_events == 0

    recalls = [row.recall for row in study.thresholds]
    assert all(a >= b for a, b in zip(recalls, recalls[1:], strict=False))
    assert [row.threshold for row in study.thresholds][0] == 0.05
    assert study.thresholds[-1].threshold == 0.95

    magnitudes = [abs(f.coefficient) for f in study.features]
    assert magnitudes == sorted(magnitudes, reverse=True)
    assert {f.key for f in study.features} == {key for key, _ in FEATURES}

    breakdown = study.precursor_breakdown
    assert breakdown.with_precursor_total + breakdown.without_precursor_total == study.split.test_failures
    assert breakdown.without_precursor_total > 0

    timeline = study.timeline
    assert timeline.machine in MACHINES
    assert all(point.hour >= 6 * 168 for point in timeline.points)
    assert study.limitations
