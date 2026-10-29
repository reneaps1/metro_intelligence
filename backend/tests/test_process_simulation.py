"""IQ-F2: deterministic process-signal simulator (app.engines.process_simulation)."""

from __future__ import annotations

import hashlib

import pytest
from app.engines.process_simulation import (
    SCENARIO_DURATION_S,
    SCENARIOS,
    SIGNALS,
    build_timeline,
    build_tree,
    generate_series,
    parse_signal_id,
    signal_id,
)
from app.engines.process_simulation.generator import (
    DIM_HOLD_COEF_MM_PER_BAR,
    DIM_MOLD_COEF_MM_PER_C,
    HOLD_WINDOW_BAR,
    INSPECTION_DELAY_S,
    MOLD_TEMP_C,
    NEST_COUNT,
    PEAK_WINDOW_BAR,
)
from app.engines.timeseries import minmax_downsample

H = 3600.0
PRIMARY = "INY-01"


def _sid(key: str, machine: str = PRIMARY) -> str:
    return signal_id(machine, key)


def _values(points: list[tuple[float, float]]) -> list[float]:
    return [v for _, v in points]


def _digest(scenario: str) -> str:
    h = hashlib.sha256()
    for signal in SIGNALS:
        for t, v in generate_series(scenario, _sid(signal.key), 0.0, SCENARIO_DURATION_S, 500).points:
            h.update(f"{t:.4f}:{v:.6f};".encode())
    return h.hexdigest()


# --- determinism ----------------------------------------------------------------


def test_same_scenario_produces_identical_output() -> None:
    first = _digest("normal")
    build_timeline.cache_clear()
    assert _digest("normal") == first


def test_scenarios_differ_from_each_other() -> None:
    digests = {_digest(s.id) for s in SCENARIOS}
    assert len(digests) == len(SCENARIOS)


def test_value_does_not_depend_on_requested_window() -> None:
    narrow = dict(generate_series("normal", _sid("barrel_temp"), 100.0, 200.0, 1000).points)
    wide = dict(generate_series("normal", _sid("barrel_temp"), 0.0, 1000.0, 5000).points)
    assert narrow[150.0] == wide[150.0]


# --- catalog / tree -------------------------------------------------------------


def test_tree_contains_every_signal_for_every_machine() -> None:
    leaves: list[dict] = []

    def walk(node: dict) -> None:
        if node["node_type"] == "signal":
            leaves.append(node)
        for child in node["children"]:
            walk(child)

    walk(build_tree())
    assert len(leaves) == 2 * len(SIGNALS)
    assert all(leaf["signal"]["source_type"] == "SIMULATED" for leaf in leaves)
    assert {leaf["signal"]["value_type"] for leaf in leaves} >= {"analog", "digital"}


def test_tree_has_plant_to_channel_hierarchy() -> None:
    tree = build_tree()
    path = [tree["node_type"]]
    node = tree
    while node["children"]:
        node = node["children"][0]
        path.append(node["node_type"])
    assert path == ["plant", "area", "line", "machine", "group", "signal"]


def test_negative_control_channels_are_flagged() -> None:
    controls = {s.key for s in SIGNALS if not s.informative}
    assert controls == {"ambient_humidity", "aux_voltage"}


@pytest.mark.parametrize(
    "bad", ["", "L1.INY-01", "L2.INY-01.mold_temp", "L1.INY-99.mold_temp", "L1.INY-01.nope"]
)
def test_unknown_signal_ids_are_rejected(bad: str) -> None:
    with pytest.raises(KeyError):
        parse_signal_id(bad)


# --- physics-flavoured shape ------------------------------------------------------


def test_cycles_are_contiguous_and_plausible() -> None:
    timeline = build_timeline("normal", PRIMARY)
    cycles = timeline.cycles
    assert 900 < len(cycles) < 1100  # ~29 s cycles over 8 h
    for prev, nxt in zip(cycles, cycles[1:], strict=False):
        assert nxt.start == pytest.approx(prev.end)
    assert {c.cavity for c in cycles} == set(range(1, NEST_COUNT + 1))
    assert all(26.0 < c.duration < 32.0 for c in cycles)


def test_injection_pressure_is_cyclic_not_white_noise() -> None:
    timeline = build_timeline("normal", PRIMARY)
    c = timeline.cycles[100]
    points = generate_series("normal", _sid("injection_pressure"), c.start, c.end, 5000).points
    peak_t, peak_v = max(points, key=lambda p: p[1])
    # Peak sits at the fill -> holding switchover, then pressure settles at the holding level.
    assert peak_t == pytest.approx(c.start + c.hold_start, abs=0.15)
    assert PEAK_WINDOW_BAR[0] < peak_v < PEAK_WINDOW_BAR[1]
    mid_hold = [v for t, v in points if c.start + c.hold_start + 2 < t < c.start + c.cool_start - 0.5]
    assert all(abs(v - c.hold_pressure) < 20 for v in mid_hold)
    idle = [v for t, v in points if t < c.start + c.fill_start]
    assert max(idle) < 30


def test_screw_returns_to_cushion_then_recovers() -> None:
    c = build_timeline("normal", PRIMARY).cycles[50]
    points = dict(generate_series("normal", _sid("screw_position"), c.start, c.end, 5000).points)
    at_switchover = points[c.start + c.hold_start]
    after_recovery = points[c.start + c.recovery_end]
    assert at_switchover == pytest.approx(c.cushion, abs=0.5)
    assert after_recovery > 60


# --- scenarios ---------------------------------------------------------------------


def test_thermal_drift_raises_mold_temperature_only_in_that_scenario() -> None:
    def mean_between(scenario: str, a: float, b: float) -> float:
        pts = generate_series(scenario, _sid("mold_temp"), a, b, 2000).points
        values = _values(pts)
        return sum(values) / len(values)

    assert mean_between("thermal_drift", 5.8 * H, 6.2 * H) > MOLD_TEMP_C + 7
    assert mean_between("normal", 5.8 * H, 6.2 * H) < MOLD_TEMP_C + 1


def test_drift_is_not_applied_to_the_comparison_machine() -> None:
    pts = generate_series("thermal_drift", _sid("mold_temp", "INY-02"), 5.8 * H, 6.2 * H, 2000).points
    assert max(_values(pts)) < MOLD_TEMP_C + 2


def test_pressure_setpoint_change_steps_holding_pressure() -> None:
    cycles = build_timeline("pressure_setpoint_change", PRIMARY).cycles
    before = [c.hold_pressure for c in cycles if c.start < 4 * H]
    after = [c.hold_pressure for c in cycles if c.start >= 4 * H]
    assert sum(before) / len(before) == pytest.approx(620, abs=3)
    assert sum(after) / len(after) == pytest.approx(560, abs=3)
    assert all(HOLD_WINDOW_BAR[0] - 20 < v < HOLD_WINDOW_BAR[1] for v in after)


def test_pressure_spikes_flag_cycles_out_of_process_window() -> None:
    cycles = build_timeline("pressure_setpoint_change", PRIMARY).cycles
    # Scripted spikes raise a machine alarm and always leave the process window.
    spiked = [c for c in cycles if c.alarm and not c.fault]
    assert len(spiked) == 4
    assert all(c.peak_pressure > PEAK_WINDOW_BAR[1] and not c.process_ok for c in spiked)
    # Wider spread after the setpoint change can also push a few unalarmed
    # cycles out of the window -- process_ok catches those too.
    out_of_window = [c for c in cycles if c.peak_pressure > PEAK_WINDOW_BAR[1]]
    assert all(not c.process_ok for c in out_of_window)


def test_intermittent_fault_scenario_has_downtime_and_drive_faults() -> None:
    timeline = build_timeline("intermittent_fault_cavity_change", PRIMARY)
    # No cycle starts inside the 20-minute insert change at 4 h.
    assert not [c for c in timeline.cycles if 4 * H <= c.start < 4 * H + 1200]
    auto = generate_series("intermittent_fault_cavity_change", _sid("auto_mode"), 3.9 * H, 4.5 * H, 2000)
    assert min(_values(auto.points)) == 0.0
    assert max(_values(auto.points)) == 1.0
    faulty = [c for c in timeline.cycles if c.fault]
    assert faulty and all(c.alarm and not c.process_ok for c in faulty)


def test_normal_scenario_is_almost_entirely_in_process_window() -> None:
    cycles = build_timeline("normal", PRIMARY).cycles
    ok_rate = sum(c.process_ok for c in cycles) / len(cycles)
    assert ok_rate > 0.99


def test_every_scenario_has_annotated_events() -> None:
    for scenario in SCENARIOS:
        assert scenario.events
        for event in scenario.events:
            assert 0 <= event.offset_s <= SCENARIO_DURATION_S
            assert event.label


# --- series sizing -------------------------------------------------------------------


@pytest.mark.parametrize("key", [s.key for s in SIGNALS])
def test_full_range_series_respects_max_points(key: str) -> None:
    result = generate_series("intermittent_fault_cavity_change", _sid(key), 0.0, SCENARIO_DURATION_S, 800)
    assert 0 < len(result.points) <= 800
    times = [t for t, _ in result.points]
    assert times == sorted(times)


def test_zoomed_window_is_raw_full_range_is_envelope() -> None:
    zoom = generate_series("normal", _sid("injection_pressure"), 3600.0, 3660.0, 2000)
    full = generate_series("normal", _sid("injection_pressure"), 0.0, SCENARIO_DURATION_S, 2000)
    assert zoom.mode == "raw" and not zoom.downsampled
    assert full.mode == "envelope" and full.downsampled


def test_envelope_keeps_pressure_peaks() -> None:
    full = generate_series(
        "pressure_setpoint_change", _sid("injection_pressure"), 0.0, SCENARIO_DURATION_S, 1000
    )
    assert max(_values(full.points)) > PEAK_WINDOW_BAR[1]


@pytest.mark.parametrize("window", [(-1.0, 10.0), (10.0, 10.0), (0.0, SCENARIO_DURATION_S + 1)])
def test_invalid_windows_are_rejected(window: tuple[float, float]) -> None:
    with pytest.raises(ValueError):
        generate_series("normal", _sid("mold_temp"), window[0], window[1], 100)


# --- downsampling ----------------------------------------------------------------------


def test_minmax_downsample_preserves_extremes_and_order() -> None:
    points = [(float(i), float((i * 37) % 101)) for i in range(10_000)]
    points[4321] = (4321.0, 999.0)
    points[777] = (777.0, -50.0)
    reduced = minmax_downsample(points, 200)
    values = _values(reduced)
    assert len(reduced) <= 200
    assert max(values) == 999.0 and min(values) == -50.0
    assert [t for t, _ in reduced] == sorted(t for t, _ in reduced)


def test_minmax_downsample_passthrough_and_validation() -> None:
    points = [(0.0, 1.0), (1.0, 2.0)]
    assert minmax_downsample(points, 10) == points
    with pytest.raises(ValueError):
        minmax_downsample(points, 1)


# --- IQ-F4: synthetic quality layer (Vista B) and alignment ------------------------------


def test_synthetic_dimension_follows_the_imposed_mechanism() -> None:
    from app.engines.process_simulation.alignment import correlate

    thermal = correlate(
        "thermal_drift", _sid("mold_temp"), _sid("dim_pins_length"), 0.0, SCENARIO_DURATION_S, "cycle", 0
    )
    assert thermal.fit.slope == pytest.approx(DIM_MOLD_COEF_MM_PER_C, rel=0.1)
    assert (thermal.fit.r_squared or 0) > 0.6
    pressure = correlate(
        "pressure_setpoint_change",
        _sid("holding_pressure"),
        _sid("dim_pins_length"),
        0.0,
        SCENARIO_DURATION_S,
        "cycle",
        0,
    )
    assert pressure.fit.slope == pytest.approx(DIM_HOLD_COEF_MM_PER_BAR, rel=0.1)
    assert thermal.causal_imposed and pressure.causal_imposed


def test_negative_control_does_not_explain_the_dimension() -> None:
    from app.engines.process_simulation.alignment import correlate

    result = correlate(
        "normal", _sid("ambient_humidity"), _sid("dim_pins_length"), 0.0, SCENARIO_DURATION_S, "cycle", 0
    )
    assert abs(result.fit.pearson_r or 0) < 0.1


def test_time_join_recovers_the_inspection_delay() -> None:
    from app.engines.process_simulation.alignment import DEFAULT_TIME_LAGS_S, correlate

    result = correlate(
        "normal",
        _sid("holding_pressure"),
        _sid("dim_pins_length"),
        0.0,
        SCENARIO_DURATION_S,
        "time",
        0,
        DEFAULT_TIME_LAGS_S,
    )
    # Joined naively by time (lag 0) the relation disappears; at the inspection delay it is back.
    assert abs(result.fit.pearson_r or 0) < 0.1
    assert result.best_lag == INSPECTION_DELAY_S
    at_delay = next(s for s in result.scan if s.lag == INSPECTION_DELAY_S)
    assert (at_delay.pearson_r or 0) < -0.2


def test_cycle_lag_scan_peaks_at_zero_for_independent_cycles() -> None:
    from app.engines.process_simulation.alignment import DEFAULT_CYCLE_LAGS, correlate

    result = correlate(
        "normal",
        _sid("holding_pressure"),
        _sid("dim_pins_length"),
        0.0,
        SCENARIO_DURATION_S,
        "cycle",
        0,
        DEFAULT_CYCLE_LAGS,
    )
    assert result.best_lag == 0
    assert len(result.pairs) <= 1500


def test_cycle_mode_rejects_different_machines() -> None:
    from app.engines.process_simulation.alignment import correlate

    with pytest.raises(ValueError):
        correlate("normal", _sid("mold_temp"), _sid("mold_temp", "INY-02"), 0.0, 3600.0, "cycle", 0)


def test_worn_nest_concentrates_synthetic_nok_until_insert_change() -> None:
    cycles = build_timeline("intermittent_fault_cavity_change", PRIMARY).cycles
    nok = [c for c in cycles if c.dim_nok]
    assert nok and all(c.cavity == 7 and c.start < 4 * H for c in nok)
    assert not [c for c in build_timeline("normal", PRIMARY).cycles if c.dim_nok]


def test_inspection_result_is_published_after_the_delay() -> None:
    timeline = build_timeline("normal", PRIMARY)
    c = timeline.cycles[200]
    series = generate_series(
        "normal", _sid("dim_pins_length"), c.start, c.start + 2 * INSPECTION_DELAY_S, 2000
    )
    assert (c.start + INSPECTION_DELAY_S, pytest.approx(c.dim_length)) in [
        (t, pytest.approx(v)) for t, v in series.points
    ]


def test_process_signals_do_not_depend_on_the_quality_layer() -> None:
    # Leakage guard: process values are drawn from their own RNG stream.
    timeline = build_timeline("thermal_drift", PRIMARY)
    first = [(c.peak_pressure, c.hold_pressure) for c in timeline.cycles[:50]]
    build_timeline.cache_clear()
    again = [(c.peak_pressure, c.hold_pressure) for c in build_timeline("thermal_drift", PRIMARY).cycles[:50]]
    assert first == again
