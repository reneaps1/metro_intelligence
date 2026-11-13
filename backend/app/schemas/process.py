"""Response schemas for the per-step process views (ADR-005)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

StepStatus = Literal["ok", "warning", "critical", "neutral"]


class OperationRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    kind: str
    side: str | None
    sequence: int


class LineRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    operations: list[OperationRead]


class RecipeRead(BaseModel):
    id: uuid.UUID
    code: int
    label: str
    variant_part_number: str | None
    variant_pending: bool


class DateRange(BaseModel):
    start: date
    end: date
    first_available: date | None
    last_available: date | None


class DailyCount(BaseModel):
    day: date
    pieces: int
    machine_nok: int
    spec_nok: int


class StepOverview(BaseModel):
    operation: OperationRead
    pieces: int
    machine_nok: int
    machine_nok_rate: float | None
    spec_nok: int
    spec_nok_rate: float | None
    first_pass_yield: float | None
    repeat_attempts: int
    has_specification: bool
    worst_cpk: float | None
    disagreements: int
    coverage: float | None
    status: StepStatus
    trend: list[DailyCount]
    # Last day with data for this step in any range: tells "no data in this
    # range" apart from "never loaded".
    last_day: date | None = None


class LineOverview(BaseModel):
    line: LineRead
    range: DateRange
    recipes: list[RecipeRead]
    selected_recipe_ids: list[uuid.UUID]
    reference_pieces: int
    steps: list[StepOverview]


class SpecLimits(BaseModel):
    nominal: Decimal
    lower_tol: Decimal | None
    upper_tol: Decimal | None
    lower_limit: Decimal | None
    upper_limit: Decimal | None


class CharacteristicSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    unit: str
    n: int
    mean: float | None
    std_dev: float | None
    min: float | None
    max: float | None
    machine_nok: int
    spec_nok: int
    machine_ok_spec_nok: int
    specification: SpecLimits | None
    cp: float | None
    cpk: float | None
    capability_kind: Literal["Cpk", "Cpu", "Cpl"] | None


class BreakdownRow(BaseModel):
    key: str
    label: str
    pieces: int
    machine_nok: int
    spec_nok: int


class OperationSummary(BaseModel):
    operation: OperationRead
    range: DateRange
    # Recipes of the line, so the step page can offer the same filter as the overview.
    recipes: list[RecipeRead] = []
    pieces: int
    machine_nok: int
    spec_nok: int
    repeat_attempts: int
    disagreements: int
    status: StepStatus
    characteristics: list[CharacteristicSummary]
    by_recipe: list[BreakdownRow]
    by_nest: list[BreakdownRow]
    trend: list[DailyCount]


class HistogramBin(BaseModel):
    lower: float
    upper: float
    count: int


class CharacteristicDailyPoint(BaseModel):
    day: date
    n: int
    mean: float
    min: float
    max: float
    spec_nok: int
    machine_nok: int
    cpk: float | None


class CharacteristicDetail(BaseModel):
    characteristic: CharacteristicSummary
    range: DateRange
    bins: list[HistogramBin]
    # Values outside the histogram range (0.5th-99.5th percentile, widened
    # to the specification limits) are counted here instead of drawn.
    below_range: int
    above_range: int
    daily: list[CharacteristicDailyPoint]


class PositionCell(BaseModel):
    """One grid cell of the X/Y position map: |dX| in [x0, x1), |dY| in [y0, y1)."""

    ix: int
    iy: int
    count: int


class PositionPoint(BaseModel):
    """One sampled pin: its |dX|, |dY| and nest."""

    x: float
    y: float
    nest: int | None


class PositionStats(BaseModel):
    """Pin position pairs of one group (whole selection or one nest).
    Medians and 95th percentiles are robust to the gross outliers stations
    sometimes log."""

    pieces: int
    out_of_tolerance: int
    out_x: int
    out_y: int
    # Radial deviation sqrt(dX^2 + dY^2) beyond the tolerance (the circle).
    out_radial: int
    machine_nok: int
    median_x: float | None
    median_y: float | None
    p95_x: float | None
    p95_y: float | None


class NestPosition(PositionStats):
    nest: int


class PositionMap(BaseModel):
    operation: OperationRead
    range: DateRange
    pin: int
    pins: list[int]
    unit: str | None
    # Drawing upper limits per axis; None when the axis has no specification.
    tolerance_x: float | None
    tolerance_y: float | None
    # Both axes run from 0 to `extent` in `bins` cells; pairs beyond it are
    # counted in `beyond_extent` and stay in every other statistic.
    extent: float
    bins: int
    cells: list[PositionCell]
    beyond_extent: int
    # Uniform random sample of the pairs inside the extent, for the point cloud.
    points: list[PositionPoint]
    sampled_from: int
    total: PositionStats
    nests: list[NestPosition]


class TraceValue(BaseModel):
    characteristic_id: uuid.UUID
    code: str
    name: str
    unit: str
    value: Decimal
    machine_ok: bool | None
    is_ok: bool | None
    deviation: Decimal | None
    specification: SpecLimits | None


class TraceStep(BaseModel):
    operation: OperationRead
    attempt: int
    recorded_at: datetime
    nest: int | None
    program_number: int | None
    machine_ok: bool | None
    values: list[TraceValue]


class PieceTrace(BaseModel):
    serial_number: str
    line: LineRead
    recipe: RecipeRead | None
    first_seen_at: datetime
    steps: list[TraceStep]
