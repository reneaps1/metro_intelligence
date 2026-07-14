"""F4.7 (MI-27): process event creation + filtered listing.

Process events feed the Risk Engine's correlation logic (F9.3) and
post-event validation (F10.4); in the demo they're mostly seeded, with
manual logging available from the measurements UI (F5.7).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.context import ProcessEvent
from app.services.audit_service import AuditContext, record_event


def create_process_event(
    db: Session,
    *,
    event_type: str,
    line_id: uuid.UUID | None,
    machine_id: uuid.UUID | None,
    occurred_at: datetime,
    description: str,
    event_metadata: dict[str, object],
    context: AuditContext,
) -> ProcessEvent:
    event = ProcessEvent(
        event_type=event_type,
        line_id=line_id,
        machine_id=machine_id,
        occurred_at=occurred_at,
        description=description,
        event_metadata=event_metadata,
    )
    db.add(event)
    db.flush()
    record_event(
        db,
        context,
        action="created",
        entity_type="context.process_event",
        entity_id=event.id,
        after={
            "event_type": event.event_type,
            "line_id": event.line_id,
            "machine_id": event.machine_id,
            "occurred_at": event.occurred_at,
            "description": event.description,
        },
    )
    return event


def list_process_events(
    db: Session,
    *,
    event_type: str | None,
    line_id: uuid.UUID | None,
    machine_id: uuid.UUID | None,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
    page: int,
    page_size: int,
) -> tuple[list[ProcessEvent], int]:
    stmt = select(ProcessEvent)
    if event_type is not None:
        stmt = stmt.where(ProcessEvent.event_type == event_type)
    if line_id is not None:
        stmt = stmt.where(ProcessEvent.line_id == line_id)
    if machine_id is not None:
        stmt = stmt.where(ProcessEvent.machine_id == machine_id)
    if occurred_from is not None:
        stmt = stmt.where(ProcessEvent.occurred_at >= occurred_from)
    if occurred_to is not None:
        stmt = stmt.where(ProcessEvent.occurred_at <= occurred_to)
    stmt = stmt.order_by(ProcessEvent.occurred_at.desc())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).scalars().all()
    return list(rows), total
