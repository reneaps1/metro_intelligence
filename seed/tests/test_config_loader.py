from __future__ import annotations

import pytest

from seed.config import load_config

EXPECTED_SCENARIOS = {
    "stable_capable",
    "slow_drift",
    "shift_after_event",
    "high_variance",
    "outlier_nok",
}


def test_loads_all_expected_scenarios() -> None:
    config = load_config()
    assert set(config.scenarios) == EXPECTED_SCENARIOS


def test_settings_are_positive() -> None:
    config = load_config()
    assert config.settings.history_days > 0
    assert config.settings.point_interval_days > 0
    assert isinstance(config.settings.default_seed, int)


def test_unknown_scenario_raises_with_available_list() -> None:
    config = load_config()
    with pytest.raises(ValueError, match="stable_capable"):
        config.scenario("does_not_exist")


def test_shift_after_event_declares_event_day_offset() -> None:
    config = load_config()
    scenario = config.scenario("shift_after_event")
    assert scenario.event_day_offset is not None
    assert 0 < scenario.event_day_offset < 90
