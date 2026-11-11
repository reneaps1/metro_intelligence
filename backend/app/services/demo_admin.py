"""Operator recovery for the demo administrator (IQ-F30 private host).

The platform has no password-change endpoint. On a demo host the operator can
set a new password and reactivate the demo administrator by setting
``SEED_DEMO_USER_RESET=true`` together with ``SEED_DEMO_USER_PASSWORD`` and
restarting; the reset runs once per start, never in production, and is
written to the audit log (no password material). Unset the flag afterwards.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.password import hash_password
from app.models import User
from app.services.audit_service import write_audit_log

MIN_PASSWORD_LENGTH = 12


def reset_demo_admin(session: Session, email: str, password: str) -> bool:
    """Set a new password and reactivate ``email``. Returns False when the user does not exist."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("demo administrator password must have at least 12 characters")
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        return False
    before = {"is_active": user.is_active}
    user.password_hash = hash_password(password)
    user.is_active = True
    write_audit_log(
        session,
        action="demo_admin_reset",
        entity_type="security.user",
        actor_identifier="system:startup",
        entity_id=user.id,
        before_state=before,
        after_state={"is_active": True, "password_changed": True},
    )
    session.commit()
    return True
