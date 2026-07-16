"""LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md): Cpk/control-limits history
over a date range, partitioned into fixed-size, non-overlapping windows of
measurement results.

Reuses the exact query shape `app.api.v1.measurements.get_characteristic_series`
already uses (join MeasurementResult -> Specification, filtered by
`characteristic_id` and an optional `measured_at` range, ordered by
`measured_at`) -- this module only adds the windowing on top, never
reimplements the range query.

A window never mixes measurement results taken against two different
specification versions: if the ordered result set crosses a spec-version
boundary partway through a window, the window closes early at that boundary
and a new one starts on the new spec, even if that leaves a short window.
This mirrors `/series`'s own principle (each result is evaluated against
the specification it was actually measured under -- `specification_id` at
import time, never the characteristic's current active spec) applied to a
windowed aggregate: mixing two spec versions' values into one Cpk/control-
limit calculation would silently blend two different tolerance definitions.

Pure aggregation over real engine output (CLAUDE.md §16, §22): every
Cpk/center-line/UCL/LCL value returned is exactly what F8.D's
`cpk()`/`individuals_moving_range_limits()` computed for that window's real
values -- never recalculated, smoothed, or approximated here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engines.spc.capability import ToleranceSpec, cpk
from app.engines.spc.control_limits import individuals_moving_range_limits
from app.models.catalog import Specification
from app.models.measurement import MeasurementResult

MIN_POINTS_FOR_STATS = 2


@dataclass(frozen=True)
class CapabilityWindow:
    window_start: datetime
    window_end: datetime
    point_count: int
    cpk: Decimal | None
    center_line: Decimal | None
    ucl: Decimal | None
    lcl: Decimal | None
    engine_name: str | None
    engine_version: str | None


def _window_from_rows(rows: list[tuple[MeasurementResult, Specification]]) -> CapabilityWindow:
    window_start = rows[0][0].measured_at
    window_end = rows[-1][0].measured_at
    point_count = len(rows)

    if point_count < MIN_POINTS_FOR_STATS:
        return CapabilityWindow(
            window_start=window_start,
            window_end=window_end,
            point_count=point_count,
            cpk=None,
            center_line=None,
            ucl=None,
            lcl=None,
            engine_name=None,
            engine_version=None,
        )

    values = [result.value for result, _spec in rows]
    # Every row in this window shares one specification (windows are split at
    # spec-version boundaries before this function ever sees them) -- any row's
    # spec is the window's spec.
    spec = rows[0][1]
    tolerance_spec = ToleranceSpec(nominal=spec.nominal, lower_tol=spec.lower_tol, upper_tol=spec.upper_tol)

    limits = individuals_moving_range_limits(values)
    try:
        cpk_value = cpk(values, tolerance_spec)
    except ValueError:
        # Undefined for a unilateral spec or a zero-variance window -- report
        # the real control limits without a Cpk rather than dropping the window.
        cpk_value = None

    return CapabilityWindow(
        window_start=window_start,
        window_end=window_end,
        point_count=point_count,
        cpk=cpk_value,
        center_line=limits.center_line,
        ucl=limits.individuals_ucl,
        lcl=limits.individuals_lcl,
        engine_name=limits.engine_name,
        engine_version=limits.engine_version,
    )


def _partition_into_windows(
    rows: list[tuple[MeasurementResult, Specification]], window_size: int
) -> list[list[tuple[MeasurementResult, Specification]]]:
    windows: list[list[tuple[MeasurementResult, Specification]]] = []
    current: list[tuple[MeasurementResult, Specification]] = []
    current_spec_id: uuid.UUID | None = None

    for row in rows:
        _result, spec = row
        if current and current_spec_id != spec.id:
            windows.append(current)
            current = []
        current.append(row)
        current_spec_id = spec.id
        if len(current) >= window_size:
            windows.append(current)
            current = []
            current_spec_id = None

    if current:
        windows.append(current)
    return windows


def compute_capability_history(
    db: Session,
    characteristic_id: uuid.UUID,
    *,
    from_: datetime | None,
    to: datetime | None,
    window_size: int,
) -> list[CapabilityWindow]:
    """Deterministic: the same (characteristic_id, range, window_size) over
    an unchanged result set always partitions into the same windows in the
    same order -- no randomness, no wall-clock dependency."""
    stmt = (
        select(MeasurementResult, Specification)
        .join(Specification, MeasurementResult.specification_id == Specification.id)
        .where(MeasurementResult.characteristic_id == characteristic_id)
    )
    if from_ is not None:
        stmt = stmt.where(MeasurementResult.measured_at >= from_)
    if to is not None:
        stmt = stmt.where(MeasurementResult.measured_at <= to)
    stmt = stmt.order_by(MeasurementResult.measured_at)

    rows = [(result, spec) for result, spec in db.execute(stmt).all()]
    windows = _partition_into_windows(rows, window_size)
    return [_window_from_rows(window_rows) for window_rows in windows]
