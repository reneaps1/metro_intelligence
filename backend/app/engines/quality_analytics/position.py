"""IQ-F19: X/Y position of a feature (e.g. a pin) against its position tolerance.

Pure and descriptive: for one `PinPair` it returns the deviations from the
nominal, the true position of every piece (TP = 2 * sqrt(dx^2 + dy^2), the
diameter of the smallest circle around the nominal that contains the point),
how many pieces fall outside each tolerance zone, and where the cloud is
centred -- overall and per group -- so a drift direction can be read off the
plot. No decision is taken here (CLAUDE.md §2).
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Literal

from app.engines.quality_analytics.analytics import (
    QualityFilter,
    piece_nok_flags,
    select,
    selected_variables,
)
from app.engines.quality_analytics.dataset import DimensionalDataset

XYGroupBy = Literal["nok", "nest", "mold_cavity"]

# Points sent to the browser; every piece still counts in the statistics.
MAX_XY_POINTS = 4000
# A point exactly on the zone boundary is inside (float noise must not flip it).
_EPS = 1e-9


def _thin(indices: list[int], cap: int) -> list[int]:
    """Deterministic stride sample of at most `cap` items (keeps order)."""
    if cap <= 0:
        return []
    step = max(1, math.ceil(len(indices) / cap))
    return indices[::step]


def _centroid(dxs: list[float], dys: list[float]) -> dict[str, float] | None:
    if not dxs:
        return None
    return {"dx": statistics.fmean(dxs), "dy": statistics.fmean(dys)}


def xy_detail(
    ds: DimensionalDataset, f: QualityFilter, pair_key: str, group_by: XYGroupBy = "nok"
) -> dict[str, Any]:
    """Deviation cloud of one X/Y pair; raises KeyError for an unknown pair."""
    pair = ds.pin_pair(pair_key)
    xs, ys = ds.values[pair.x], ds.values[pair.y]
    idx_all = select(ds, f)
    keys = [v.key for v in selected_variables(ds, f)]
    verdicts = piece_nok_flags(ds, f, idx_all, keys)
    nok_of = {i: bool(v) for i, v in zip(idx_all, verdicts, strict=True)}
    idx = [i for i in idx_all if xs[i] is not None and ys[i] is not None]

    def dev(i: int) -> tuple[float, float]:
        return (
            float(xs[i]) * pair.scale - pair.nominal_x,  # type: ignore[arg-type]
            float(ys[i]) * pair.scale - pair.nominal_y,  # type: ignore[arg-type]
        )

    devs = {i: dev(i) for i in idx}
    tps = [2 * math.hypot(*devs[i]) for i in idx]
    n = len(idx)

    circles = []
    for c in pair.circles:
        outside = sum(1 for tp in tps if tp > c.diameter + _EPS)
        circles.append(
            {
                "label": c.label,
                "diameter": c.diameter,
                "outside": outside,
                "outside_rate": outside / n if n else None,
            }
        )
    box_outside = None
    if pair.tol_xy is not None:
        t = pair.tol_xy + _EPS
        box_outside = sum(1 for i in idx if abs(devs[i][0]) > t or abs(devs[i][1]) > t)

    group_col: list[int | None] | None = (
        ds.cavities if group_by == "nest" else ds.mold_cavities if group_by == "mold_cavity" else None
    )
    buckets: dict[Any, list[int]] = defaultdict(list)
    for i in idx:
        g = ("NOK" if nok_of[i] else "OK") if group_col is None else group_col[i]
        if g is not None:
            buckets[g].append(i)
    groups = [
        {
            "group": g,
            "pieces": len(members),
            "nok": sum(1 for i in members if nok_of[i]),
            "centroid": _centroid([devs[i][0] for i in members], [devs[i][1] for i in members]),
        }
        for g, members in sorted(buckets.items(), key=lambda kv: str(kv[0]).zfill(8))
    ]

    # NOK pieces are rare and are the point of the plot: sample them apart so
    # thinning never hides them, then fill the rest of the budget with OK ones.
    nok_idx = [i for i in idx if nok_of[i]]
    ok_idx = [i for i in idx if not nok_of[i]]
    kept_nok = _thin(nok_idx, MAX_XY_POINTS // 2)
    kept = sorted(kept_nok + _thin(ok_idx, MAX_XY_POINTS - len(kept_nok)))
    points = [
        [
            round(devs[i][0], 6),
            round(devs[i][1], 6),
            None if group_col is None else group_col[i],
            nok_of[i],
        ]
        for i in kept
    ]

    reported = ds.nok_basis == "reported"
    return {
        "pair": {
            "key": pair.key,
            "label": pair.label,
            "unit": pair.unit,
            "nominal_x": pair.nominal_x,
            "nominal_y": pair.nominal_y,
            "tol_xy": pair.tol_xy,
        },
        "group_by": group_by,
        "pieces": n,
        "nok_pieces": len(nok_idx),
        "nok_label": "pieza NOK según el veredicto de la máquina"
        if reported
        else "pieza NOK (alguna cota fuera de tolerancia)",
        "circles": circles,
        "box_outside": box_outside,
        "box_outside_rate": (box_outside / n if n else None) if box_outside is not None else None,
        "tp": {
            "median": statistics.median(tps) if tps else None,
            "p95": statistics.quantiles(tps, n=20, method="inclusive")[18] if len(tps) >= 2 else None,
            "max": max(tps) if tps else None,
        },
        "centroid": _centroid([devs[i][0] for i in idx], [devs[i][1] for i in idx]),
        "nok_centroid": _centroid([devs[i][0] for i in nok_idx], [devs[i][1] for i in nok_idx]),
        "groups": groups,
        "points": points,
        "points_total": n,
    }
