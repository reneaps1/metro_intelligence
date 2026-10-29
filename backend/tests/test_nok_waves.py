"""IQ-F7: NOK waves -- persistence rule and per-episode evaluation."""

from __future__ import annotations

from app.engines.experimental_ml.nok_waves import (
    Episode,
    GroupPoint,
    alert_runs,
    evaluate_episodes,
    persistence_alerts,
)
from app.services.predictive_service import cusum_study, wave_episodes, wave_study


def _series(noks: list[int]) -> list[GroupPoint]:
    return [GroupPoint(ts=float(i), pieces=12, nok_pieces=n) for i, n in enumerate(noks)]


def test_persistence_rule_reads_only_the_past_window() -> None:
    #            0  1  2  3  4  5  6  7
    noks = [0, 1, 0, 2, 1, 0, 0, 0]
    # window 3, threshold 3: sums -> 0,1,1,3,3,3,1,0
    assert persistence_alerts(_series(noks), window=3, threshold=3) == [3, 4, 5]
    # Changing the future never changes an earlier alert.
    assert persistence_alerts(_series([*noks[:4], 9, 9, 9, 9]), window=3, threshold=3)[:1] == [3]


def test_alert_runs_debounce_contiguous_alerts() -> None:
    assert alert_runs([7, 3, 4, 5, 9]) == [(3, 5), (7, 7), (9, 9)]


def test_episode_statuses_delay_and_false_alarms() -> None:
    episodes = [Episode(10, 19), Episode(40, 49), Episode(70, 79)]
    alerts = [
        8,  # 2 groups before the first episode (horizon 3) -> anticipated
        9,
        10,
        43,  # 3 groups into the second -> detected, 7/10 of the wave still ahead
        44,
        60,  # far from any episode -> false alarm
    ]
    ev = evaluate_episodes(alerts, episodes, horizon=3)
    first, second, third = ev.episodes
    assert (first.status, first.delay_groups, first.remaining_share) == ("anticipated", -2, 1.0)
    assert (second.status, second.delay_groups, second.remaining_share) == ("detected", 3, 0.7)
    assert (third.status, third.first_alert) == ("missed", None)
    assert ev.alert_events == [(8, 10), (43, 44), (60, 60)]
    assert ev.false_alarm_events == 1
    assert (ev.anticipated, ev.detected, ev.missed) == (1, 1, 1)


def test_alert_after_the_episode_is_not_a_detection() -> None:
    ev = evaluate_episodes([20], [Episode(10, 19)], horizon=3)
    assert ev.episodes[0].status == "missed"
    assert ev.false_alarm_events == 1


def test_synthetic_waves_are_detected_but_never_anticipated() -> None:
    assert len(wave_episodes("INY-01")) == 3
    assert len(wave_episodes("INY-02")) == 1
    for machine in ("INY-01", "INY-02"):
        study = wave_study(machine, window=5, threshold=4, horizon=15)
        ev = study.evaluation
        assert ev.anticipated == 0
        assert ev.detected == len(study.episodes)
        # Detection happens early: most of each wave is still ahead.
        assert all(e.remaining_share is not None and e.remaining_share > 0.8 for e in ev.episodes)
        assert ev.false_alarm_events > 0
        assert sum(h.pieces for h in study.hours) == sum(p.pieces for p in study.series)


def test_cusum_flags_the_first_pin_position_wave() -> None:
    study = cusum_study("INY-01", "PinPositionY", 0.5, 4.0)
    assert study.result is not None
    assert study.result.drift_direction == "upward"
    # First INY-01 wave starts at day 1.4 (hour 33.6): alarm within the following hours.
    assert 33 <= (study.result.drift_index or 0) <= 40
    assert len(study.timestamps) == len(study.result.points) == 168
