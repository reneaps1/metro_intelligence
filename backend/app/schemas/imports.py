"""F4.5 (MI-25): request/response schemas for the file import pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class QuarantinedRowRead(BaseModel):
    id: uuid.UUID
    row_number: int
    raw_row: dict[str, Any]
    reason: str

    model_config = {"from_attributes": True}


class ImportedFileRead(BaseModel):
    id: uuid.UUID
    original_filename: str
    sha256: str
    size_bytes: int
    content_type: str | None
    parse_status: str
    error_detail: str | None
    created_at: datetime
    runs_created: int
    samples_created: int
    results_created: int
    quarantined_rows: list[QuarantinedRowRead]

    model_config = {"from_attributes": True}
