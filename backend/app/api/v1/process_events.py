"""F4.7 (MI-27): process event registration + query API.

Scope (Notion MI-27): POST/GET only, filtered by type/time-window/machine/
line -- no update/delete (events are append-only observations, consistent
with CLAUDE.md §6's immutability rule for anything feeding downstream
engines).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.security import User
from app.schemas.context import Page, ProcessEventCreate, ProcessEventRead
from app.services.audit_service import AuditContext, get_audit_context
from app.services.process_event_service import create_process_event, list_process_events

router = APIRouter(prefix="/process-events", tags=["process-events"])


@router.get("", response_model=Page[ProcessEventRead])
def list_events(
    event_type: str | None = None,
    line_id: uuid.UUID | None = None,
    machine_id: uuid.UUID | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("context.process_event", "read")),
) -> Page[ProcessEventRead]:
    rows, total = list_process_events(
        db,
        event_type=event_type,
        line_id=line_id,
        machine_id=machine_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        page=page,
        page_size=page_size,
    )
    return Page(
        items=[ProcessEventRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProcessEventRead, status_code=201)
def create_event(
    payload: ProcessEventCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("context.process_event", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> ProcessEventRead:
    event = create_process_event(
        db,
        event_type=payload.event_type,
        line_id=payload.line_id,
        machine_id=payload.machine_id,
        occurred_at=payload.occurred_at,
        description=payload.description,
        event_metadata=payload.event_metadata,
        context=context,
    )
    db.commit()
    return ProcessEventRead.model_validate(event)
