"""IQ-F13: calendar fields of the simulator and the `real_calendar` builder (fictitious data)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from app.engines.process_simulation import (
    MACHINES,
    SCENARIOS,
    build_timeline,
    generate_series,
    get_scenario,
    scenario_events,
    signal_id,
)
from app.engines.process_simulation.alignment import correlate
from app.engines.process_simulation.calendar_scenario import (
    CALENDAR_SCENARIO_ID,
    CALENDAR_SCENARIO_NAME,
    MIN_HOUR_PIECES,
    build_calendar_scenario,
    hourly_nok_rates,
    mold_delta,
)
from app.engines.process_simulation.catalog import get_signal
from app.engines.process_simulation.generator import (
    GENERATOR_VERSION,
    NEST_COUNT,
    SCENARIO_DURATION_S,
    SCENARIO_START,
    _piecewise,
    causal_imposed,
    scenario_duration,
    scenario_start,
)

H = 3600
BASE = 1_767_603_600  # fictitious plant period, a whole UTC hour
OFFSET = -5 * H  # plant time = UTC - 5 h (whole hours: plant hours = UTC hours)
PRIMARY, OTHER = MACHINES

# (pieces, NOK) per plant hour after BASE; hour 2 has too few pieces and ends in a long stop.
HOURS = [(120, 6), (120, 6), (50, 0), (120, 60), (120, 50), (120, 6)]
LONG_GAP_AFTER_S = 2 * H + 15 + 30 * 49  # last piece of hour 2
LONG_GAP_S = 3 * H + 15 - LONG_GAP_AFTER_S  # until the first piece of hour 3 (35.5 min)
SHORT_GAP = range(40, 60)  # 20 pieces skipped in hour 4: a 10.5 min gap, not a stop


def _pieces() -> tuple[list[float], list[bool]]:
    ts: list[float] = []
    nok: list[bool] = []
    for hour, (count, bad) in enumerate(HOURS):
        slots = [k for k in range(count) if not (hour == 4 and k in SHORT_GAP)]
        for i, k in enumerate(slots):
            ts.append(BASE + hour * H + 15 + 30 * k)
            nok.append(i < bad)
    return ts, nok


@pytest.fixture(scope="module")
def calendar():
    ts, nok = _pieces()
    return build_calendar_scenario(ts, nok, 8, OFFSET)


# --------------------------------------------------------------------------- static scenarios


def test_static_scenarios_keep_the_fixed_calendar() -> None:
    assert GENERATOR_VERSION == "process-sim-1.2.0"
    for s in SCENARIOS:
        assert (s.start, s.duration_s, s.nest_count, s.quality_driven) == (None, None, None, False)
        assert scenario_start(s) == SCENARIO_START and scenario_duration(s) == SCENARIO_DURATION_S
    assert CALENDAR_SCENARIO_ID not in {s.id for s in SCENARIOS}
    with pytest.raises(KeyError):
        get_scenario(CALENDAR_SCENARIO_ID)


def test_string_ids_and_scenario_objects_give_the_same_timeline() -> None:
    by_id = build_timeline("thermal_drift", PRIMARY.code)
    by_object = build_timeline(get_scenario("thermal_drift"), PRIMARY.code)
    assert by_id.cycles == by_object.cycles
    assert scenario_events(get_scenario("normal")) == scenario_events("normal")


# --------------------------------------------------------------------------- builder


def test_start_is_floored_to_the_minute_and_duration_covers_the_last_piece(calendar) -> None:
    assert calendar.start == datetime.fromtimestamp(BASE, tz=UTC)  # first piece at BASE + 15 s
    last_piece = BASE + 5 * H + 15 + 30 * 119
    assert calendar.duration_s == last_piece - BASE + 60
    assert calendar.id == CALENDAR_SCENARIO_ID and calendar.name == CALENDAR_SCENARIO_NAME
    assert calendar.quality_driven is True and calendar.nest_count == 8
    assert calendar.events == ()


def test_downtimes_are_the_gaps_of_twenty_minutes_or_more(calendar) -> None:
    assert calendar.downtimes == ((LONG_GAP_AFTER_S, LONG_GAP_S),)


def test_no_cycle_starts_inside_a_downtime_and_the_line_restarts_after_it(calendar) -> None:
    timeline = build_timeline(calendar, PRIMARY.code)
    ((stop, length),) = calendar.downtimes
    assert not [c for c in timeline.cycles if stop <= c.start < stop + length]
    assert any(c.start == stop + length for c in timeline.cycles)
    assert timeline.cycles[-1].end <= calendar.duration_s
    assert timeline.cycles[-1].end > calendar.duration_s - 60  # runs until the end of the calendar


def test_nest_count_is_used_on_the_primary_machine_only(calendar) -> None:
    assert {c.cavity for c in build_timeline(calendar, PRIMARY.code).cycles} == set(range(1, 9))
    assert {c.cavity for c in build_timeline(calendar, OTHER.code).cycles} == set(range(1, NEST_COUNT + 1))


def test_mold_delta_follows_the_smoothed_hourly_rate(calendar) -> None:
    p_ref = 128 / 630  # all pieces, including the short hour
    # Hour 2 has < 100 pieces: it neither gets a point nor smooths its neighbours.
    # Hour 4 has exactly 100 pieces (the short gap removed 20): it still counts.
    smoothed = {0: 0.05, 1: 0.05, 3: 0.5, 4: (0.5 + 0.5 + 0.05) / 3, 5: (0.5 + 0.05) / 2}
    expected = {h: min(8.0, max(-2.0, 4.0 * (r / p_ref - 1.0))) for h, r in smoothed.items()}
    assert expected[0] == -2.0  # clamped
    points = calendar.mold_temp_delta
    inner = points[1:-1]
    assert [t for t, _ in inner] == [h * H + H / 2 for h in expected]
    for (_, value), h in zip(inner, expected, strict=True):
        assert value == pytest.approx(expected[h])
    # 0 before the first and after the last point, linear in between.
    assert _piecewise(points, 0.0) == 0.0
    assert _piecewise(points, 5 * H + H / 2 + 1) == 0.0
    assert _piecewise(points, 4 * H) == pytest.approx((expected[3] + expected[4]) / 2)
    assert _piecewise(points, 2 * H + H / 2) == pytest.approx((expected[1] + expected[3]) / 2)


def test_mold_delta_gain_and_clamp() -> None:
    assert mold_delta(0.1, 0.1) == 0.0
    assert mold_delta(0.15, 0.1) == pytest.approx(2.0)
    assert mold_delta(1.0, 0.1) == 8.0
    assert mold_delta(0.0, 0.1) == -2.0


def test_hours_are_plant_time() -> None:
    ts = [BASE + 100.0] * MIN_HOUR_PIECES + [BASE + 2000.0] * MIN_HOUR_PIECES
    nok = [True] * MIN_HOUR_PIECES + [False] * MIN_HOUR_PIECES
    assert list(hourly_nok_rates(ts, nok, 0).values()) == [0.5]
    # Plant time = UTC + 30 min: the second half of the pieces falls in the next plant hour.
    assert sorted(hourly_nok_rates(ts, nok, 1800).values()) == [0.0, 1.0]


def test_builder_is_deterministic_and_validates_inputs() -> None:
    ts, nok = _pieces()
    first = build_calendar_scenario(ts, nok, 8, OFFSET)
    assert build_calendar_scenario(list(reversed(ts)), list(reversed(nok)), 8, OFFSET) == first
    build_timeline.cache_clear()
    again = build_timeline(build_calendar_scenario(ts, nok, 8, OFFSET), PRIMARY.code)
    build_timeline.cache_clear()
    assert build_timeline(first, PRIMARY.code).cycles == again.cycles
    without_nok = build_calendar_scenario(ts, [False] * len(ts), None, OFFSET)
    assert without_nok.mold_temp_delta == ((0.0, 0.0),) and without_nok.nest_count is None
    for bad in (([], [], 8), (ts, nok[:-1], 8), (ts, nok, 0)):
        with pytest.raises(ValueError):
            build_calendar_scenario(bad[0], bad[1], bad[2], OFFSET)


# --------------------------------------------------------------------------- quality-driven scenario


def test_only_the_mold_temperature_carries_the_quality_driven_delta(calendar) -> None:
    flat = replace(calendar, mold_temp_delta=((0.0, 0.0),))
    driven = build_timeline(calendar, PRIMARY.code).cycles
    control = build_timeline(flat, PRIMARY.code).cycles
    # Same seed and calendar: peak pressure and the Vista B dimension do not inherit the delta.
    assert [(c.peak_pressure, c.hold_pressure, c.dim_length) for c in driven] == [
        (c.peak_pressure, c.hold_pressure, c.dim_length) for c in control
    ]
    mold = signal_id(PRIMARY.code, "mold_temp")
    t = 4 * H
    assert (
        generate_series(calendar, mold, t, t + 60, 100).points[0][1]
        > generate_series(flat, mold, t, t + 60, 100).points[0][1]
    )


def test_causal_imposed_only_for_the_driven_mold_temperature(calendar) -> None:
    mold, hold = get_signal("mold_temp"), get_signal("holding_pressure")
    assert causal_imposed(calendar, PRIMARY, mold) is True
    assert causal_imposed(calendar, OTHER, mold) is False
    assert causal_imposed(calendar, PRIMARY, hold) is False
    assert causal_imposed(get_scenario("thermal_drift"), PRIMARY, mold) is False
    assert causal_imposed(get_scenario("normal"), PRIMARY, get_signal("dim_nok")) is True


def test_series_and_alignment_accept_the_calendar_scenario(calendar) -> None:
    mold = signal_id(PRIMARY.code, "mold_temp")
    hold = signal_id(PRIMARY.code, "holding_pressure")
    late = calendar.duration_s - 600
    assert generate_series(calendar, hold, late, calendar.duration_s, 200).points
    # The window is checked against the scenario's own duration (6 h here), not the 8 h default.
    assert calendar.duration_s + 1 < SCENARIO_DURATION_S
    with pytest.raises(ValueError):
        generate_series(calendar, hold, late, calendar.duration_s + 1, 200)
    result = correlate(calendar, mold, hold, 0.0, calendar.duration_s, "cycle", 0)
    assert result.causal_imposed is True and result.fit.n > 100
