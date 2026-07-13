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

from pydantic import BaseModel


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
