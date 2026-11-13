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
