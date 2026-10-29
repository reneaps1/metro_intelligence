"""IQ-F19: X/Y position against the position tolerance (hand-checked, fictitious data)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.connectors.pin_spec import read_pin_spec
from app.engines.quality_analytics import (
    DimensionalDataset,
    QualityFilter,
    Variable,
    position,
    synthetic_dataset,
)
from app.engines.quality_analytics.dataset import PinPair, ToleranceCircle, check_pin_pairs
from app.engines.quality_analytics.position import xy_detail
from app.engines.quality_analytics.synthetic import BAD_COMBO_SHIFT_MM, BAD_MOLD_CAVITIES, critical_nest

PAIR = PinPair(
    "pin",
    "Pin",
    "px",
    "py",
    nominal_x=-1.0,
    nominal_y=2.0,
    tol_xy=0.1,
    circles=(ToleranceCircle("Plano", 0.2), ToleranceCircle("Fin de línea", 0.5)),
    scale=0.01,
)


def _ds(pairs: tuple[PinPair, ...] = (PAIR,)) -> DimensionalDataset:
    # Raw values in hundredths of a mm around the nominal (-1.00, 2.00); the last piece has no X.
    px: list[float | None] = [-90.0, -100.0, -130.0, -100.0, None]
    py: list[float | None] = [200.0, 205.0, 200.0, 200.0, 200.0]
    n = len(px)
    return DimensionalDataset(
        id="t",
        name="t",
        description="t",
        source_type="REAL",
        variables=(
            Variable("px", "X", "", 0.0, None, None, nominal_given=False),
            Variable("py", "Y", "", 0.0, None, None, nominal_given=False),
        ),
        timestamps=[float(i) for i in range(n)],
        group_ids=list(range(n)),
        machines=[None] * n,
        cavities=[1, 1, 2, 2, 2],
        shifts=[None] * n,
        batches=[None] * n,
        values={"px": px, "py": py},
        reported_nok=[False, True, False, False, True],
        mold_cavities=[5, 6, 5, 6, 5],
        nok_basis="reported",
        has_groups=False,
        pin_pairs=pairs,
    )


def test_true_position_zones_and_centroids_are_hand_checked() -> None:
    # Deviations (mm): (+0.10, 0), (0, +0.05), (-0.30, 0), (0, 0) -> TP 0.2, 0.1, 0.6, 0.0
    d = xy_detail(_ds(), QualityFilter(), "pin")
    assert d["pieces"] == 4  # the piece without X is left out
    assert d["nok_pieces"] == 1
    # 0.2 lies exactly on the 0.2 circle: inside. Only 0.6 is outside both circles.
    assert [(c["label"], c["outside"]) for c in d["circles"]] == [("Plano", 1), ("Fin de línea", 1)]
    assert d["circles"][0]["outside_rate"] == pytest.approx(0.25)
    assert d["box_outside"] == 1  # |dx| = 0.10 is on the box edge: inside
    assert d["tp"]["max"] == pytest.approx(0.6)
    assert d["tp"]["median"] == pytest.approx(0.15)
    assert d["centroid"]["dx"] == pytest.approx(-0.05) and d["centroid"]["dy"] == pytest.approx(0.0125)
    assert d["nok_centroid"] == pytest.approx({"dx": 0.0, "dy": 0.05})
    assert [g["group"] for g in d["groups"]] == ["OK", "NOK"]
    got = sorted((round(p[0], 6), round(p[1], 6)) for p in d["points"])
    assert got == [(-0.3, 0.0), (0.0, 0.0), (0.0, 0.05), (0.1, 0.0)]


def test_grouping_by_nest_or_mold_cavity_and_filters() -> None:
    by_nest = xy_detail(_ds(), QualityFilter(), "pin", "nest")
    groups = {g["group"]: g for g in by_nest["groups"]}
    assert groups[1]["pieces"] == 2 and groups[1]["nok"] == 1
    assert groups[2]["centroid"] == pytest.approx({"dx": -0.15, "dy": 0.0})
    assert {p[2] for p in by_nest["points"]} == {1, 2}
    by_mold = xy_detail(_ds(), QualityFilter(), "pin", "mold_cavity")
    assert {g["group"] for g in by_mold["groups"]} == {5, 6}
    only_nest_2 = xy_detail(_ds(), QualityFilter(cavities=frozenset({2})), "pin")
    assert only_nest_2["pieces"] == 2 and only_nest_2["circles"][0]["outside"] == 1


def test_thinning_never_hides_nok_pieces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(position, "MAX_XY_POINTS", 2)
    d = xy_detail(_ds(), QualityFilter(), "pin")
    assert len(d["points"]) == 2 and d["points_total"] == 4
    assert sum(1 for p in d["points"] if p[3]) == 1


def test_pin_pairs_are_validated() -> None:
    with pytest.raises(KeyError):
        xy_detail(_ds(), QualityFilter(), "nope")
    with pytest.raises(ValueError, match="two distinct"):
        _ds((PinPair("pin", "Pin", "px", "zz", 0.0, 0.0, None, ()),))
    with pytest.raises(ValueError, match="unique"):
        check_pin_pairs((PAIR, PAIR), {"px": [], "py": []})
    with pytest.raises(ValueError, match="non-positive"):
        _ds((PinPair("pin", "Pin", "px", "py", 0.0, 0.0, None, (ToleranceCircle("x", 0.0),)),))


def test_synthetic_pin_pair_shows_the_critical_nest_drift() -> None:
    ds = synthetic_dataset()
    assert [p.key for p in ds.pin_pairs] == ["pin"]
    d = xy_detail(ds, QualityFilter(), "pin", "nest")
    centroids = {g["group"]: g["centroid"]["dx"] for g in d["groups"]}
    crit = critical_nest()
    others = [dx for nest, dx in centroids.items() if nest != crit]
    # Mechanisms in synthetic.py: the critical nest's X is shifted +0.010 mm, plus
    # BAD_COMBO_SHIFT_MM on the pieces it receives from the bad mold cavities (IQ-F20).
    nest_molds = [m for n, m in zip(ds.cavities, ds.mold_cavities or [], strict=True) if n == crit]
    bad_share = sum(1 for m in nest_molds if m in BAD_MOLD_CAVITIES) / len(nest_molds)
    expected = 0.010 + bad_share * BAD_COMBO_SHIFT_MM
    assert centroids[crit] - sum(others) / len(others) == pytest.approx(expected, abs=0.002)
    assert len(d["points"]) <= position.MAX_XY_POINTS


def test_private_spec_file_is_parsed_and_validated(tmp_path: Path) -> None:
    spec = {
        "format": "pin-spec-v1",
        "pin_pairs": [
            {
                "key": "pin_a",
                "label": "Pin A",
                "x": "px",
                "y": "py",
                "scale": 0.01,
                "nominal_x": -1.0,
                "nominal_y": 2.0,
                "tol_xy": 0.1,
                "circles": [{"label": "Plano", "diameter": 0.2}],
            }
        ],
    }
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    (pair,) = read_pin_spec(path)
    assert pair.scale == 0.01 and pair.circles == (ToleranceCircle("Plano", 0.2),)
    spec["pin_pairs"][0]["circles"] = [{"label": "x", "diameter": -1}]  # type: ignore[index]
    path.write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError):
        read_pin_spec(path)
