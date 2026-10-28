"""IQ-F5: dimensional quality analytics engine (hand-checked small datasets)."""

from __future__ import annotations

import pytest
from app.engines.quality_analytics import (
    DimensionalDataset,
    QualityFilter,
    Variable,
    overview,
    synthetic_dataset,
    variable_detail,
)
from app.engines.quality_analytics.analytics import select, wilson_interval
from app.engines.quality_analytics.synthetic import NEST_COUNT, critical_nest

DAY = 86_400.0
LEN = Variable("len", "Longitud", "mm", 10.0, -0.1, 0.1)
FLAT = Variable("flat", "Planitud", "mm", 0.0, None, 0.05)
NOTOL = Variable("ref", "Referencia", "mm", 5.0, None, None)


def _ds() -> DimensionalDataset:
    # 2 days x 2 cavities x 3 pieces. Cavity 2 on day 1 has 2 NOK lengths.
    ts, groups, cav, mach, shift, batch = [], [], [], [], [], []
    length, flat, ref = [], [], []
    g = 0
    for day in range(2):
        for piece in range(3):
            g += 1
            for c in (1, 2):
                ts.append(day * DAY + piece * 60)
                groups.append(g)
                cav.append(c)
                mach.append("M1" if c == 1 else "M2")
                shift.append("A")
                batch.append(None)
                bad = day == 0 and c == 2 and piece < 2
                length.append(10.2 if bad else 10.0 + 0.01 * piece)
                flat.append(0.06 if (day == 1 and c == 1 and piece == 0) else 0.01)
                ref.append(5.0 + piece)
    return DimensionalDataset(
        id="t",
        name="t",
        description="t",
        source_type="REAL",
        variables=(LEN, FLAT, NOTOL),
        timestamps=ts,
        group_ids=groups,
        machines=mach,
        cavities=cav,
        shifts=shift,
        batches=batch,
        values={"len": length, "flat": flat, "ref": ref},
    )


def test_tolerance_checks_both_sides_and_unilateral() -> None:
    assert LEN.is_nok(10.2) and LEN.is_nok(9.8) and not LEN.is_nok(10.1)
    assert FLAT.is_nok(0.06) and not FLAT.is_nok(-1.0)
    assert not NOTOL.is_nok(999.0) and not NOTOL.has_tolerance
    assert not LEN.is_nok(None)


def test_overview_counts_and_definitions() -> None:
    o = overview(_ds(), QualityFilter())
    s = o["summary"]
    assert (s["groups"], s["pieces"], s["nok_pieces"], s["measurement_nok"]) == (6, 12, 3, 3)
    assert s["nok_rate"] == pytest.approx(3 / 12)
    assert s["measurements"] == 36
    assert "al menos una" in s["nok_definition"]
    assert s["top_variables"] == ["len", "flat"]


def test_variable_selection_changes_the_nok_definition() -> None:
    s = overview(_ds(), QualityFilter(variables=("flat",)))["summary"]
    assert s["nok_pieces"] == 1 and s["variables_counted"] == ["flat"]


def test_pareto_is_sorted_with_cumulative_share() -> None:
    pareto = overview(_ds(), QualityFilter())["pareto"]
    assert [(r["variable"], r["nok"], r["above"]) for r in pareto] == [
        ("len", 2, 2),
        ("flat", 1, 1),
        ("ref", 0, 0),
    ]
    assert pareto[0]["cumulative_pct"] == pytest.approx(2 / 3)
    assert pareto[1]["cumulative_pct"] == pytest.approx(1.0)


def test_by_cavity_rate_ci_and_relative_risk() -> None:
    rows = {r["cavity"]: r for r in overview(_ds(), QualityFilter())["by_cavity"]}
    assert rows[2]["rate"] == pytest.approx(2 / 6)
    assert rows[1]["rate"] == pytest.approx(1 / 6)
    assert rows[2]["relative_risk"] == pytest.approx(2.0)
    assert rows[2]["ci_low"] < rows[2]["rate"] < rows[2]["ci_high"]


def test_trend_by_day_and_shift() -> None:
    by_day = overview(_ds(), QualityFilter(), "day")["trend"]
    assert [(b["bucket"], b["pieces"], b["nok"]) for b in by_day] == [
        ("1970-01-01", 6, 2),
        ("1970-01-02", 6, 1),
    ]
    by_shift = overview(_ds(), QualityFilter(), "shift")["trend"]
    assert [(b["bucket"], b["pieces"]) for b in by_shift] == [("Turno A", 12)]


def test_filters_select_pieces() -> None:
    ds = _ds()
    assert len(select(ds, QualityFilter(cavities=frozenset({2})))) == 6
    assert len(select(ds, QualityFilter(machines=frozenset({"M1"}), start=DAY))) == 3
    assert overview(ds, QualityFilter(start=DAY))["summary"]["nok_pieces"] == 1


def test_wilson_interval_reference_values() -> None:
    low, high = wilson_interval(10, 100)  # textbook: 0.0552 .. 0.1744
    assert low == pytest.approx(0.0552, abs=1e-3)
    assert high == pytest.approx(0.1744, abs=1e-3)
    assert wilson_interval(0, 0) is None
    assert wilson_interval(0, 50)[0] == 0.0


def test_variable_detail_spec_vs_control_limits_and_capability() -> None:
    d = variable_detail(_ds(), QualityFilter(), "len", "cavity")
    assert d["spec"] == {"nominal": 10.0, "lsl": 9.9, "usl": 10.1, "unit": "mm"}
    assert d["control_limits"]["engine"].startswith("spc_engine")
    assert d["capability"]["cp"] is not None and d["capability"]["cpk"] is not None
    assert [g["group"] for g in d["groups"]] == ["1", "2"]
    assert sum(b["count"] for b in d["histogram"]) == d["n"] == 12
    assert d["nok"] == 2


def test_capability_rules_for_unilateral_and_missing_tolerances() -> None:
    flat = variable_detail(_ds(), QualityFilter(), "flat")["capability"]
    assert flat["cp"] is None and flat["cpk"] is not None and "unilateral" in flat["reason"]
    ref = variable_detail(_ds(), QualityFilter(), "ref")["capability"]
    assert ref == {"cp": None, "cpk": None, "reason": "Sin tolerancias: no se calcula capacidad."}


def test_missing_metadata_disables_filters() -> None:
    assert _ds().available_filters() == {
        "machine": True,
        "cavity": True,
        "shift": True,
        "batch": False,
        "mold_cavity": False,
        "station": False,
        "quality_flags": False,
    }


def test_columns_must_have_equal_length() -> None:
    with pytest.raises(ValueError):
        DimensionalDataset(
            id="x",
            name="x",
            description="x",
            source_type="REAL",
            variables=(LEN,),
            timestamps=[0.0],
            group_ids=[1],
            machines=[None],
            cavities=[None],
            shifts=[None],
            batches=[None],
            values={"len": []},
        )


# --- synthetic demo dataset ---------------------------------------------------------------


def test_synthetic_dataset_is_deterministic_and_shaped() -> None:
    ds = synthetic_dataset()
    assert ds.source_type == "SIMULATED"
    assert len(ds) == 60_480 and ds.distinct(ds.cavities) == list(range(1, NEST_COUNT + 1))
    assert ds.mechanisms
    s1 = overview(ds, QualityFilter())["summary"]
    from app.engines.quality_analytics.synthetic import _build

    _build.cache_clear()
    assert overview(synthetic_dataset(), QualityFilter())["summary"] == s1


def test_synthetic_critical_nest_stands_out() -> None:
    o = overview(synthetic_dataset(), QualityFilter())
    worst = o["summary"]["worst_cavity"]
    assert worst["cavity"] == critical_nest()
    assert worst["relative_risk"] > 5
    others = [c["rate"] for c in o["by_cavity"] if c["cavity"] != critical_nest()]
    assert max(others) < worst["ci_low"]  # separation is beyond the 95 % interval
    assert o["pareto"][0]["variable"] in {"PinsLength", "PinPositionY"}


def test_synthetic_tool_wear_lowers_daily_cpk_until_tool_change() -> None:
    days = variable_detail(
        synthetic_dataset(), QualityFilter(machines=frozenset({"INY-01"})), "HousingWidth"
    )["cpk_by_day"]
    cpks = [d["cpk"] for d in days]
    assert cpks[3] < cpks[0] and cpks[4] > cpks[3]


def test_critical_nest_is_configurable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_CRITICAL_NEST", "9")
    assert critical_nest() == 9
    assert overview(synthetic_dataset(), QualityFilter())["summary"]["worst_cavity"]["cavity"] == 9
    monkeypatch.setenv("DEMO_CRITICAL_NEST", "99")
    assert critical_nest() == 4
