from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid7


class ProcessEvent(Base):
    __tablename__ = "context_process_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('tool_change', 'maintenance', 'material_lot_change', 'machine_adjustment')",
            name="ck_context_process_events_event_type",
        ),
        Index("ix_context_process_events_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    line_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_lines.id", ondelete="SET NULL"), nullable=True
    )
    machine_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_machines.id", ondelete="SET NULL"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
