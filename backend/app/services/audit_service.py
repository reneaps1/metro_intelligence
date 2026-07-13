"""F4.3 (MI-23): central audit service.

CLAUDE.md §5/§23 require an audit trail for logins, permission changes, master
data changes, and every recommendation/decision. This module is the one place
that writes ``security_audit_log`` rows so that contract is uniform and hard
to forget: every service that writes master data, users/roles, or decisions
should depend on ``get_audit_context`` and call ``record_event``/
``record_change`` instead of constructing ``AuditLog`` rows by hand.

``write_audit_log`` is the low-level primitive (used directly by
``app.api.v1.auth`` for login/logout events, which happen before a request
has a resolved actor -- e.g. a failed login has no authenticated user).
``record_event``/``record_change`` build on it once an ``AuditContext`` is
available.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.models.security import AuditLog, User

# Keys stripped from before/after payloads regardless of caller intent, so a
# careless call site can't leak credentials into the audit trail (F4.3
# acceptance criterion: "Sin PII innecesaria en las entradas").
_SENSITIVE_KEYS = frozenset(
    {"password", "password_hash", "token", "access_token", "refresh_token", "secret", "jwt_secret"}
)


def _json_safe(value: Any) -> Any:
    """Recursively coerce values into what the ``before_state``/``after_state``
    JSONB columns can actually store. Callers routinely pass ORM column values
    straight through (UUID foreign keys, Decimal tolerances, datetime
    timestamps) -- none of those are JSON-serializable as-is, so without this
    conversion the write raises deep inside the DB driver instead of at a
    call site that's easy to debug."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _strip_sensitive(state: dict[str, Any] | None) -> dict[str, Any] | None:
    if state is None:
        return None
    cleaned = {k: _json_safe(v) for k, v in state.items() if k not in _SENSITIVE_KEYS}
    return cleaned or None


@dataclass(frozen=True)
class AuditContext:
    """The actor/IP resolved once per request for audit purposes."""

    actor_user_id: uuid.UUID | None
    actor_identifier: str | None
    ip_address: str | None


def get_audit_context(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> AuditContext:
    """FastAPI dependency resolving the real authenticated actor + client IP.

    Depend on this (alongside ``require_permission``) in any endpoint that
    writes master data, decisions, or user/role changes, then pass the
    result to ``record_event``/``record_change`` -- this is what makes the
    audit entry's actor the real request actor rather than a value the
    service layer has to reconstruct itself.
    """
    return AuditContext(
        actor_user_id=current_user.id,
        actor_identifier=current_user.email,
        ip_address=request.client.host if request.client else None,
    )


def write_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    actor_user_id: uuid.UUID | None = None,
    actor_identifier: str | None = None,
    entity_id: uuid.UUID | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Low-level primitive: append one audit_log row. Does not commit --
    callers control the transaction boundary alongside their own writes."""
    entry = AuditLog(
        actor_user_id=actor_user_id,
        actor_identifier=actor_identifier,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry


def record_event(
    db: Session,
    context: AuditContext,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an audit_log row for ``context``'s actor. Does not commit."""
    return write_audit_log(
        db,
        action=action,
        entity_type=entity_type,
        actor_user_id=context.actor_user_id,
        actor_identifier=context.actor_identifier,
        entity_id=entity_id,
        before_state=_strip_sensitive(before),
        after_state=_strip_sensitive(after),
        ip_address=context.ip_address,
    )


def record_change(
    db: Session,
    context: AuditContext,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID,
    before: dict[str, Any],
    after: dict[str, Any],
) -> AuditLog:
    """Record an update, capturing only the fields that actually changed.

    Diffing once here (rather than at each call site) is what keeps
    "before/after correctos" uniform across every master-data service: pass
    the full before/after dict and this computes the delta.
    """
    changed_keys = {key for key in after if before.get(key) != after.get(key)}
    changed_before = {key: before.get(key) for key in changed_keys}
    changed_after = {key: after.get(key) for key in changed_keys}
    return record_event(
        db,
        context,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=changed_before,
        after=changed_after,
    )
