"""F4.7 (MI-27): request/response schemas for process events."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ProcessEventType = Literal["tool_change", "maintenance", "material_lot_change", "machine_adjustment"]

# Prevents an oversized JSONB blob from being pushed through this endpoint
# (CLAUDE.md §5 file/input validation, and this task's own "Seguridad"
# note: "validación de metadata (tamaño máximo JSONB)").
MAX_METADATA_BYTES = 8192


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class ProcessEventCreate(BaseModel):
    event_type: ProcessEventType
    line_id: uuid.UUID | None = None
    machine_id: uuid.UUID | None = None
    occurred_at: datetime
    description: str = Field(min_length=1, max_length=2000)
    event_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_metadata")
    @classmethod
    def _limit_metadata_size(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value)) > MAX_METADATA_BYTES:
            raise ValueError(f"event_metadata must serialize to at most {MAX_METADATA_BYTES} bytes.")
        return value


class ProcessEventRead(BaseModel):
    id: uuid.UUID
    event_type: str
    line_id: uuid.UUID | None
    machine_id: uuid.UUID | None
    occurred_at: datetime
    description: str
    event_metadata: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
