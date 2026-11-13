"""IQ-F14: line alarm engine (R1-R4) -- hand-computed vectors on fictitious sequences."""

from __future__ import annotations

import pytest
from app.engines.line_alarms.rules import (
    ENGINE_VERSION,
    LineAlarm,
    LineRuleConfig,
    evaluate_line,
)

# Rules that must stay silent in a vector are pushed out of reach.
# Hand vectors check raise/clear without the deadband unless a test asks for it.
QUIET = {
    "run_limit": 1000,
    "nest_window": 1000,
    "rate_window": 1000,
    "cavity_window": 1000,
    "clear_fraction": 1.0,
}


def _cfg(**values: float) -> LineRuleConfig:
    return LineRuleConfig(**{**QUIET, **values})  # type: ignore[arg-type]


def _ts(n: int) -> list[float]:
    return [1_000.0 + 10 * i for i in range(n)]


def _only(alarms: list[LineAlarm], rule: str) -> list[LineAlarm]:
    return [a for a in alarms if a.rule == rule]


def test_version_is_experimental() -> None:
    assert ENGINE_VERSION.endswith("-experimental")


# --------------------------------------------------------------------------- R1


def test_r1_streak_raises_at_the_limit_and_clears_on_the_next_ok() -> None:
    nok = [False, True, True, True, True, True, True, False, True]
    nests = [1, 2, 3, 1, 2, 3, 1, 2, 3]
    stations = [None, "a", "b", "a", "b", "c", "a", None, "a"]
    ts = _ts(len(nok))
    ev = evaluate_line(ts, nests, None, nok, stations, _cfg(run_limit=5))
    assert ev.state.run == [0, 1, 2, 3, 4, 5, 6, 0, 1]
    (a,) = _only(ev.alarms, "R1")
    assert (a.priority, a.key) == (1, None)
    assert a.raised_index == 5 and a.raised_ts == ts[5]
    assert a.evidence_from_index == 1 and a.evidence_from_ts == ts[1]  # first NOK of the streak
    assert a.cleared_index == 7 and a.cleared_ts == ts[7]
    assert (a.value, a.peak, a.limit) == (5.0, 6.0, 5.0)  # peak = final streak length
    assert a.nests == (2, 3, 1, 2, 3)  # nest of each streak piece 1..5 (up to the raise)
    assert a.station == "c"  # first failing station of the raising piece


def test_r1_still_active_at_the_end_and_short_streaks() -> None:
    nok = [True] * 4 + [False] + [True] * 7
    ev = evaluate_line(_ts(len(nok)), [None] * len(nok), None, nok, [None] * len(nok), _cfg(run_limit=5))
    (a,) = _only(ev.alarms, "R1")  # the streak of 4 never raises
    assert a.raised_index == 9 and a.evidence_from_index == 5
    assert a.cleared_index is None and a.cleared_ts is None
    assert a.peak == 7.0 and a.nests == () and a.station is None


# --------------------------------------------------------------------------- R2


def test_r2_nest_ratio_against_the_pooled_rest_with_min_nok() -> None:
    # Two alternating nests, windows of 4 pieces, ratio >= 2 and >= 2 NOK.
    nests = [1, 2] * 7
    nok = [False, False, True, True, True, False, False, False, True, False, False, True, False, False]
    stations = [f"s{i}" for i in range(len(nok))]
    ev = evaluate_line(
        _ts(len(nok)), nests, None, nok, stations, _cfg(nest_window=4, nest_min_nok=2, nest_factor=2.0)
    )
    # Index 6: nest 1 full (2 NOK of 4), nest 2 has 3 pieces with 1 NOK -> 0.5 / (1/3) = 1.5.
    assert ev.state.nest_ratio[5] is None and ev.state.nest_ratio_nest[5] is None
    assert ev.state.nest_ratio[6] == pytest.approx(1.5) and ev.state.nest_ratio_nest[6] == 1
    (a,) = _only(ev.alarms, "R2")
    # Index 7 is a piece of nest 2: it completes the rest (1 NOK in 4) and nest 1 reaches 2.0x.
    assert (a.priority, a.key, a.raised_index, a.station) == (2, 1, 7, "s7")
    assert a.evidence_from_index == 0  # first piece of nest 1's window
    assert a.value == pytest.approx(2.0) and a.limit == 2.0
    assert a.peak == pytest.approx(3.0)  # index 8: 3 NOK of 4 vs 1 of 4
    assert a.cleared_index == 12  # nest 1 drops to 1 NOK (< min)
    assert a.nests == ()


def test_r2_needs_min_nok_and_a_full_window_and_stays_finite() -> None:
    nests = [1, 2] * 6
    nok = [True, False] * 6  # nest 1 always NOK, nest 2 never
    cfg = _cfg(nest_window=4, nest_min_nok=5, nest_factor=2.0)
    ev = evaluate_line(_ts(len(nok)), nests, None, nok, [None] * len(nok), cfg)
    assert _only(ev.alarms, "R2") == []  # 4 NOK in a window of 4 never reaches the minimum of 5
    ev = evaluate_line(
        _ts(len(nok)), nests, None, nok, [None] * len(nok), _cfg(nest_window=4, nest_min_nok=4)
    )
    (a,) = _only(ev.alarms, "R2")
    # Raised when the rest is comparable (nest 2 has pieces), not while nest 1's window fills.
    assert a.raised_index == 6 and a.evidence_from_index == 0
    # The rest has no NOK: its count is floored at half a piece -> (4/4) / (0.5/3) = 6.
    assert a.value == pytest.approx(6.0)
    assert a.cleared_index is None


# --------------------------------------------------------------------------- R3


def test_r3_rate_relative_to_p_ref_on_a_full_window() -> None:
    nok = [False, False, False, True, True, True, False, False, False, False]
    stations = [None, None, None, "a", "b", "c", None, None, None, None]
    ts = _ts(len(nok))
    ev = evaluate_line(
        ts, [None] * 10, None, nok, stations, _cfg(rate_window=4, rate_factor=2.0), reference_nok_rate=0.25
    )
    assert ev.rate_limit == 0.5 and ev.reference_nok_rate == 0.25
    assert ev.state.rate[:3] == [None, None, None]  # window not full yet
    assert ev.state.rate[3:] == [0.25, 0.5, 0.75, 0.75, 0.5, 0.25, 0.0]
    (a,) = _only(ev.alarms, "R3")
    assert (a.priority, a.key, a.raised_index, a.evidence_from_index) == (2, None, 4, 1)
    assert (a.value, a.peak, a.limit, a.station) == (0.5, 0.75, 0.5, "b")
    assert a.cleared_index == 8 and a.cleared_ts == ts[8]
    # Same sequence, higher reference: 0.75 < 2 x 0.4.
    ev = evaluate_line(
        ts, [None] * 10, None, nok, stations, _cfg(rate_window=4, rate_factor=2.0), reference_nok_rate=0.4
    )
    assert _only(ev.alarms, "R3") == []


def test_r3_waits_for_a_full_window_and_never_fires_without_nok() -> None:
    nok = [True, True, True, False, False, False]
    ev = evaluate_line(_ts(6), [None] * 6, None, nok, [None] * 6, _cfg(rate_window=4), reference_nok_rate=0.1)
    (a,) = _only(ev.alarms, "R3")
    assert a.raised_index == 3 and a.evidence_from_index == 0  # first full window, not piece 0
    ok = [False] * 6
    ev = evaluate_line(_ts(6), [None] * 6, None, ok, [None] * 6, _cfg(rate_window=4))
    assert ev.reference_nok_rate == 0.0 and ev.alarms == []  # limit 0 would fire on every window


# --------------------------------------------------------------------------- R4


def test_r4_cavity_rate_relative_to_p_ref_only_with_mold_cavities() -> None:
    molds = [1, 2] * 4
    nok = [True, False, False, False, False, False, False, False]
    cfg = _cfg(cavity_window=3, cavity_factor=3.0)
    ev = evaluate_line(_ts(8), [None] * 8, molds, nok, ["x"] + [None] * 7, cfg, reference_nok_rate=0.1)
    assert ev.has_mold_cavities and ev.cavity_limit == pytest.approx(0.3)
    (a,) = _only(ev.alarms, "R4")
    assert (a.priority, a.key, a.raised_index, a.evidence_from_index) == (3, 1, 4, 0)
    assert a.value == pytest.approx(1 / 3) and a.peak == pytest.approx(1 / 3)
    assert a.cleared_index == 6  # cavity 1's window (2, 4, 6) has no NOK
    assert ev.state.cavity_rate[:4] == [None] * 4
    assert ev.state.cavity_rate[4] == pytest.approx(1 / 3) and ev.state.cavity_worst[4] == 1
    assert ev.state.cavity_rate[6] == 0.0 and ev.state.cavity_worst[6] == 1  # tie -> lowest cavity
    for molds_column in (None, [None] * 8):
        ev = evaluate_line(_ts(8), [None] * 8, molds_column, nok, [None] * 8, cfg, reference_nok_rate=0.1)
        assert not ev.has_mold_cavities and _only(ev.alarms, "R4") == []
        assert ev.state.cavity_rate == [None] * 8 and ev.state.cavity_worst == [None] * 8


# --------------------------------------------------------------------------- defaults and validation


def test_default_config_and_p_ref_from_the_sequence() -> None:
    cfg = LineRuleConfig()
    assert (cfg.run_limit, cfg.nest_window, cfg.nest_factor, cfg.nest_min_nok) == (5, 100, 3.0, 25)
    assert (cfg.rate_window, cfg.rate_factor, cfg.cavity_window, cfg.cavity_factor) == (200, 2.5, 150, 3.0)
    assert cfg.clear_fraction == 0.75
    nok = [i % 4 == 0 for i in range(400)]
    ev = evaluate_line(_ts(400), [1 + i % 3 for i in range(400)], None, nok, [None] * 400)
    assert ev.reference_nok_rate == 0.25 and ev.rate_limit == 0.625
    assert ev.alarms == []  # a steady line, NOK spread evenly over the nests, never alarms
    assert ev.state.nest_ratio[-1] == pytest.approx(1.0, abs=0.15)
    assert ev.state.rate[198] is None and ev.state.rate[199] == 0.25


def test_deadband_keeps_an_alarm_until_the_value_drops_below_its_share_of_the_limit() -> None:
    # R3 limit = 2 x 0.25 = 0.5 over 8 pieces; with the deadband it holds down to 0.375 (3/8).
    nok = [True] * 4 + [False] * 5 + [True] + [False] * 2

    def r3(fraction: float) -> list[tuple[int, int | None]]:
        cfg = _cfg(rate_window=8, rate_factor=2.0, clear_fraction=fraction)
        ev = evaluate_line(_ts(12), [None] * 12, None, nok, [None] * 12, cfg, reference_nok_rate=0.25)
        return [(a.raised_index, a.cleared_index) for a in _only(ev.alarms, "R3")]

    assert r3(1.0) == [(7, 8)]
    assert r3(0.75) == [(7, 10)]
    with pytest.raises(ValueError):
        LineRuleConfig(clear_fraction=0.0)


def test_alarms_are_in_raise_order() -> None:
    nok = [True] * 6 + [False] * 4
    ev = evaluate_line(
        _ts(10), [None] * 10, None, nok, [None] * 10, _cfg(run_limit=2, rate_window=4), reference_nok_rate=0.1
    )
    assert [(a.rule, a.raised_index) for a in ev.alarms] == [("R1", 1), ("R3", 3)]


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        evaluate_line([0.0, 1.0], [1], None, [True, False], [None, None])
    with pytest.raises(ValueError):
        evaluate_line([1.0, 0.0], [1, 1], None, [True, False], [None, None])
    with pytest.raises(ValueError):
        evaluate_line([0.0], [1], None, [True], [None], reference_nok_rate=1.5)
    with pytest.raises(ValueError):
        LineRuleConfig(run_limit=0)
