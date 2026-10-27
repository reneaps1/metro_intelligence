"""Pure aggregations over a `DimensionalDataset` (IQ-F5).

Definitions are explicit and returned with the results, so the UI can always
show the denominator and what "NOK" means:

- A *measurement* is NOK when its value is outside the variable's tolerance.
- A *piece* is NOK when at least one of the selected variables is NOK.
- Relative risk of a nest = its piece NOK rate / pooled rate of the other
  selected nests. Association only -- it says nothing about cause.

Capability (Cp/Cpk) and I-MR control limits reuse the existing SPC engines
and are only computed when the variable has tolerances / enough values.
Specification limits (LSL/USL) and control limits (UCL/LCL) are reported
separately and must never be confused.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from app.engines.quality_analytics.dataset import DimensionalDataset, Variable
from app.engines.spc.capability import ToleranceSpec, cp, cpk
from app.engines.spc.control_limits import individuals_moving_range_limits

Granularity = Literal["day", "hour", "shift"]
GroupBy = Literal["cavity", "machine", "shift", "batch"]

NOK_DEFINITION = "Pieza NOK = al menos una de las cotas seleccionadas fuera de tolerancia."
MIN_PIECES_FOR_RANKING = 30
MIN_VALUES_FOR_DAILY_CPK = 30
HISTOGRAM_BINS = 30
MAX_SERIES_POINTS = 1500


@dataclass(frozen=True)
class QualityFilter:
    start: float | None = None
    end: float | None = None
    machines: frozenset[str] | None = None
    cavities: frozenset[int] | None = None
    shifts: frozenset[str] | None = None
    batches: frozenset[str] | None = None
    # Variables that count towards piece NOK; None = all.
    variables: tuple[str, ...] | None = None


def select(ds: DimensionalDataset, f: QualityFilter) -> list[int]:
    out = []
    for i, ts in enumerate(ds.timestamps):
        if f.start is not None and ts < f.start:
            continue
        if f.end is not None and ts >= f.end:
            continue
        if f.machines is not None and ds.machines[i] not in f.machines:
            continue
        if f.cavities is not None and ds.cavities[i] not in f.cavities:
            continue
        if f.shifts is not None and ds.shifts[i] not in f.shifts:
            continue
        if f.batches is not None and ds.batches[i] not in f.batches:
            continue
        out.append(i)
    return out


def selected_variables(ds: DimensionalDataset, f: QualityFilter) -> list[Variable]:
    if f.variables is None:
        return list(ds.variables)
    return [ds.variable(key) for key in f.variables]  # KeyError on unknown keys


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95 % Wilson score interval for a proportion k/n (well-behaved for small k)."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _rate(k: int, n: int) -> float | None:
    return k / n if n else None


def _bucket(ts: float, shift: str | None, granularity: Granularity) -> tuple[str, float | None]:
    dt = datetime.fromtimestamp(ts, tz=UTC)
    if granularity == "day":
        day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return day.strftime("%Y-%m-%d"), day.timestamp()
    if granularity == "hour":
        hour = dt.replace(minute=0, second=0, microsecond=0)
        return hour.strftime("%Y-%m-%dT%H:00"), hour.timestamp()
    return f"Turno {shift or '—'}", None


def overview(ds: DimensionalDataset, f: QualityFilter, granularity: Granularity = "day") -> dict[str, Any]:
    idx = select(ds, f)
    variables = selected_variables(ds, f)
    keys = [v.key for v in variables]
    flags = [any(ds.nok[k][i] for k in keys) for i in idx]
    pieces = len(idx)
    nok_pieces = sum(flags)

    # --- trend ---
    buckets: dict[str, list[Any]] = {}
    for i, bad in zip(idx, flags, strict=True):
        label, start = _bucket(ds.timestamps[i], ds.shifts[i], granularity)
        entry = buckets.setdefault(label, [start, 0, 0])
        entry[1] += 1
        entry[2] += bad
    trend = [
        {"bucket": label, "start": start, "pieces": n, "nok": k, "rate": _rate(k, n)}
        for label, (start, n, k) in sorted(buckets.items())
    ]

    # --- pareto (measurement level) ---
    pareto_rows = []
    measurements = 0
    for v in variables:
        column = ds.values[v.key]
        above = below = valid = 0
        for i in idx:
            x = column[i]
            if x is None:
                continue
            valid += 1
            if v.usl is not None and x > v.usl:
                above += 1
            elif v.lsl is not None and x < v.lsl:
                below += 1
        measurements += valid
        pareto_rows.append(
            {
                "variable": v.key,
                "name": v.name,
                "nok": above + below,
                "above": above,
                "below": below,
                "measurements": valid,
            }
        )
    pareto_rows.sort(key=lambda r: (-r["nok"], r["variable"]))
    total_nok = sum(r["nok"] for r in pareto_rows)
    cumulative = 0
    for row in pareto_rows:
        cumulative += row["nok"]
        row["cumulative_pct"] = cumulative / total_nok if total_nok else None

    # --- by cavity + heatmap ---
    cav_counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    cell_counts: dict[tuple[int, str], int] = defaultdict(int)
    for i, bad in zip(idx, flags, strict=True):
        cav = ds.cavities[i]
        if cav is None:
            continue
        cav_counts[cav][0] += 1
        cav_counts[cav][1] += bad
        for k in keys:
            if ds.nok[k][i]:
                cell_counts[(cav, k)] += 1
    by_cavity = []
    for cav in sorted(cav_counts):
        n, k = cav_counts[cav]
        rest_n = sum(c[0] for c2, c in cav_counts.items() if c2 != cav)
        rest_k = sum(c[1] for c2, c in cav_counts.items() if c2 != cav)
        rest_rate = _rate(rest_k, rest_n)
        rate = _rate(k, n)
        ci = wilson_interval(k, n)
        by_cavity.append(
            {
                "cavity": cav,
                "pieces": n,
                "nok": k,
                "rate": rate,
                "ci_low": ci[0] if ci else None,
                "ci_high": ci[1] if ci else None,
                "relative_risk": (rate / rest_rate) if rate is not None and rest_rate else None,
            }
        )
    heatmap = [
        {
            "cavity": cav,
            "variable": k,
            "pieces": cav_counts[cav][0],
            "nok": cell_counts[(cav, k)],
            "rate": _rate(cell_counts[(cav, k)], cav_counts[cav][0]),
        }
        for cav in sorted(cav_counts)
        for k in keys
    ]

    ranked = [c for c in by_cavity if c["pieces"] >= MIN_PIECES_FOR_RANKING and c["rate"] is not None]
    worst = max(ranked, key=lambda c: c["rate"]) if ranked else None
    period = (ds.timestamps[idx[0]], ds.timestamps[idx[-1]]) if idx else (None, None)
    summary = {
        "groups": len({ds.group_ids[i] for i in idx}),
        "pieces": pieces,
        "measurements": measurements,
        "ok_pieces": pieces - nok_pieces,
        "nok_pieces": nok_pieces,
        "nok_rate": _rate(nok_pieces, pieces),
        "nok_rate_ci": wilson_interval(nok_pieces, pieces),
        "measurement_nok": total_nok,
        "top_variables": [r["variable"] for r in pareto_rows if r["nok"] > 0][:3],
        "worst_cavity": worst,
        "period_start": period[0],
        "period_end": period[1],
        "nok_definition": NOK_DEFINITION,
        "variables_counted": keys,
    }
    return {
        "summary": summary,
        "trend": trend,
        "pareto": pareto_rows,
        "by_cavity": by_cavity,
        "heatmap": heatmap,
    }


def _box(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    n = len(ordered)
    if n == 1:
        q1 = median = q3 = ordered[0]
    else:
        q1, median, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    iqr = q3 - q1
    lo_fence, hi_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = [x for x in ordered if lo_fence <= x <= hi_fence]
    return {
        "n": n,
        "min": ordered[0],
        "q1": q1,
        "median": median,
        "q3": q3,
        "max": ordered[-1],
        "whisker_low": inside[0] if inside else ordered[0],
        "whisker_high": inside[-1] if inside else ordered[-1],
        "outliers": n - len(inside),
        "mean": statistics.fmean(ordered),
    }


def _capability(values: list[float], v: Variable) -> dict[str, Any]:
    if not v.has_tolerance:
        return {"cp": None, "cpk": None, "reason": "Sin tolerancias: no se calcula capacidad."}
    if len(values) < 2:
        return {"cp": None, "cpk": None, "reason": "Datos insuficientes."}
    decimals = [Decimal(str(x)) for x in values]
    spec = ToleranceSpec(
        nominal=Decimal(str(v.nominal)),
        lower_tol=None if v.lower_tol is None else Decimal(str(v.lower_tol)),
        upper_tol=None if v.upper_tol is None else Decimal(str(v.upper_tol)),
    )
    try:
        cpk_value: float | None = float(cpk(decimals, spec))
    except ValueError:
        cpk_value = None
    try:
        cp_value: float | None = float(cp(decimals, spec))
    except ValueError:
        cp_value = None  # unilateral tolerance or zero spread
    reason = None if cp_value is not None else "Cp no aplica a tolerancia unilateral; se reporta solo Cpk."
    return {
        "cp": cp_value,
        "cpk": cpk_value,
        "reason": reason if v.has_tolerance and cpk_value is not None else reason,
    }


def variable_detail(
    ds: DimensionalDataset, f: QualityFilter, key: str, group_by: GroupBy = "cavity"
) -> dict[str, Any]:
    v = ds.variable(key)
    column = ds.values[key]
    idx = [i for i in select(ds, f) if column[i] is not None]
    values = [float(column[i]) for i in idx]  # type: ignore[arg-type]
    spec = {"nominal": v.nominal, "lsl": v.lsl, "usl": v.usl, "unit": v.unit}
    if not values:
        return {"variable": key, "name": v.name, "spec": spec, "n": 0}

    nok_count = sum(ds.nok[key][i] for i in idx)
    lo = min([*values, *(x for x in (v.lsl, v.usl) if x is not None)])
    hi = max([*values, *(x for x in (v.lsl, v.usl) if x is not None)])
    width = (hi - lo) / HISTOGRAM_BINS or 1.0
    counts = [0] * HISTOGRAM_BINS
    for x in values:
        counts[min(int((x - lo) / width), HISTOGRAM_BINS - 1)] += 1
    histogram = [{"x0": lo + b * width, "x1": lo + (b + 1) * width, "count": c} for b, c in enumerate(counts)]

    limits = individuals_moving_range_limits([Decimal(str(x)) for x in values]) if len(values) >= 2 else None
    control = (
        {
            "center_line": float(limits.center_line),
            "ucl": float(limits.individuals_ucl),
            "lcl": float(limits.individuals_lcl),
            "engine": f"{limits.engine_name} {limits.engine_version}",
        }
        if limits
        else None
    )

    step = max(1, math.ceil(len(idx) / MAX_SERIES_POINTS))
    series = [[round(ds.timestamps[i] * 1000), float(column[i]), ds.nok[key][i]] for i in idx[::step]]  # type: ignore[arg-type]

    column_for = {"cavity": ds.cavities, "machine": ds.machines, "shift": ds.shifts, "batch": ds.batches}[
        group_by
    ]
    grouped: dict[Any, list[float]] = defaultdict(list)
    grouped_nok: dict[Any, int] = defaultdict(int)
    for i in idx:
        g = column_for[i]
        if g is None:
            continue
        grouped[g].append(float(column[i]))  # type: ignore[arg-type]
        grouped_nok[g] += ds.nok[key][i]
    groups = [
        {"group": str(g), **_box(vals), "nok": grouped_nok[g], "nok_rate": grouped_nok[g] / len(vals)}
        for g, vals in sorted(grouped.items())
    ]

    by_day: dict[str, list[float]] = defaultdict(list)
    for i in idx:
        by_day[datetime.fromtimestamp(ds.timestamps[i], tz=UTC).strftime("%Y-%m-%d")].append(float(column[i]))  # type: ignore[arg-type]
    cpk_by_day = [
        {
            "day": day,
            "n": len(vals),
            "cpk": _capability(vals, v)["cpk"] if len(vals) >= MIN_VALUES_FOR_DAILY_CPK else None,
        }
        for day, vals in sorted(by_day.items())
    ]

    return {
        "variable": key,
        "name": v.name,
        "spec": spec,
        "n": len(values),
        "nok": nok_count,
        "nok_rate": nok_count / len(values),
        "mean": statistics.fmean(values),
        "std": statistics.stdev(values) if len(values) >= 2 else None,
        "min": min(values),
        "max": max(values),
        "capability": _capability(values, v),
        "control_limits": control,
        "histogram": histogram,
        "series": series,
        "series_thinned": step > 1,
        "group_by": group_by,
        "groups": groups,
        "cpk_by_day": cpk_by_day,
    }
