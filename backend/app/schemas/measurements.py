"""F4.6 (MI-26): request/response schemas for the read-only measurements API.

``deviation``/``is_ok`` are computed here at read time from the stored
``value`` against the ``Specification`` the result was actually measured
against (``MeasurementResult.specification_id``, set once at import time and
never re-evaluated later -- CLAUDE.md §6). This is a plain boundary check
for display, not the future Compliance engine (F7.D): no rule/model
versioning, no persisted verdict, no audit trail -- just arithmetic over
data that already exists, recomputed fresh on every read.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class SpecificationSnapshot(BaseModel):
    """The exact spec a result was measured against -- not necessarily the
    characteristic's *current* active spec, since a long date range can
    cross a version change (docs/tasks/F4.6.md)."""

    id: uuid.UUID
    nominal: Decimal
    lower_tol: Decimal | None
    upper_tol: Decimal | None
    unit: str
    valid_from: datetime
    valid_to: datetime | None

    model_config = {"from_attributes": True}


class MeasurementResultRead(BaseModel):
    id: uuid.UUID
    characteristic_id: uuid.UUID
    measured_at: datetime
    value: Decimal
    deviation: Decimal
    is_ok: bool
    specification: SpecificationSnapshot

    model_config = {"from_attributes": True}


class MeasurementSampleRead(BaseModel):
    id: uuid.UUID
    sample_sequence: int
    serial_number: str | None
    results: list[MeasurementResultRead]

    model_config = {"from_attributes": True}


class MeasurementRunRead(BaseModel):
    id: uuid.UUID
    measurement_program_id: uuid.UUID
    part_number_id: uuid.UUID
    machine_id: uuid.UUID | None
    imported_file_id: uuid.UUID | None
    operator_identifier: str | None
    batch_lot: str | None
    run_at: datetime
    sample_count: int

    model_config = {"from_attributes": True}


class MeasurementRunDetailRead(MeasurementRunRead):
    samples: list[MeasurementSampleRead]


class SeriesPoint(BaseModel):
    result_id: uuid.UUID
    measured_at: datetime
    value: Decimal
    deviation: Decimal
    is_ok: bool
    sample_index: int
    specification: SpecificationSnapshot


class SeriesResponse(BaseModel):
    characteristic_id: uuid.UUID
    unit: str
    total_points: int
    returned_points: int
    downsampled: bool
    points: list[SeriesPoint]


class CapabilityWindowRead(BaseModel):
    """One non-overlapping window's real Cp/control-limit output (F8.D). All
    five numeric fields are null together when the window has fewer than 2
    points -- not enough to estimate a standard deviation/moving range at
    all, not just Cpk specifically (LM.4, docs/tasks/LM4-live-monitor-deep-dive.md).

    `nominal` is the specification this window's rows were actually measured
    under -- a window can close early at a spec-version boundary, so this can
    differ from the characteristic's *current* active spec. Callers must use
    this nominal (never the current one) to convert `center_line`/`ucl`/`lcl`
    into deviation-space, or the converted values are silently offset by the
    nominal delta between spec versions."""

    window_start: datetime
    window_end: datetime
    point_count: int
    cpk: Decimal | None
    center_line: Decimal | None
    ucl: Decimal | None
    lcl: Decimal | None
    engine_name: str | None
    engine_version: str | None
    nominal: Decimal | None

    model_config = {"from_attributes": True}


class CapabilityHistoryResponse(BaseModel):
    characteristic_id: uuid.UUID
    unit: str
    window_size: int
    windows: list[CapabilityWindowRead]


class CusumPointRead(BaseModel):
    index: int
    value: Decimal
    cusum_high: Decimal
    cusum_low: Decimal

    model_config = {"from_attributes": True}


class ExperimentalDriftRead(BaseModel):
    """Phase 13 preview (CLAUDE.md §22) -- a real, shadow-mode CUSUM drift
    result over the same Cpk-window series `CapabilityHistoryResponse`
    returns. Never persisted, never feeds an Alert/Recommendation."""

    drift_detected: bool
    drift_direction: str | None
    drift_index: int | None
    target: Decimal
    stdev: Decimal
    k: Decimal
    h: Decimal
    points: list[CusumPointRead]
    rationale: str
    engine_name: str
    engine_version: str

    model_config = {"from_attributes": True}


class SamplingRecommendation(BaseModel):
    """EXPERIMENTAL (Thompson-Sampling adaptive inspection sampling
    frequency recommender, CLAUDE.md §22): read-only, purely advisory,
    never overrides `app.schemas.intelligence.RecommendationRead`/the real
    Decision flow. `characteristic_id` is `str`, not `uuid.UUID` like every
    other schema in this file -- a deliberate exception, honoring the
    literal shape this experimental surface was specified with. Safe here
    specifically because this schema is always built by direct
    construction in `adaptive_sampling_service.py` (`str(characteristic_id)`),
    never via `model_validate(..., from_attributes=True)` against an ORM
    row."""

    characteristic_id: str
    recommended_frequency: int
    current_cpk: float
    cpk_trend: Literal["stable", "improving", "declining"]
    confidence: float = Field(ge=0.0, le=1.0)
    windows_analyzed: int
    conflicting_recommendations: list[dict[str, Any]] | None = None
