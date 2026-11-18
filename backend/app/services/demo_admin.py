"""Operator recovery for the demo administrator (IQ-F30 private host).

The platform has no password-change endpoint. On a demo host the operator can
set a new password and reactivate the demo administrator by setting
``SEED_DEMO_USER_RESET=true`` together with ``SEED_DEMO_USER_PASSWORD`` and
restarting; the reset runs once per start, never in production, and is
written to the audit log (no password material). Unset the flag afterwards.

``SEED_DEMO_USERS_RESET_ALL=true`` does the same for every user at once, to
end a round of demo credentials: all accounts get the new password, nobody is
reactivated or deactivated, and each change is audited. Sessions opened
before the reset keep working until their tokens expire; rotate ``JWT_SECRET``
to end them at once.

``SEED_DEMO_USER_LOGIN_ALIAS`` (for example ``admin``) is a short login name
accepted in place of the demo administrator's email. It names the same
account: no second user, same password, same lockout and audit trail. Never
honoured in production.
"""

from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.password import hash_password
from app.models import User
from app.services.audit_service import write_audit_log

MIN_PASSWORD_LENGTH = 12
DEMO_ADMIN_EMAIL = "luis.torres@demo.local"


def resolve_login_alias(identifier: str) -> str:
    """Return the demo administrator's email when ``identifier`` is its configured alias."""
    alias = os.getenv("SEED_DEMO_USER_LOGIN_ALIAS", "").strip().lower()
    if alias and get_settings().app_env != "production" and identifier.strip().lower() == alias:
        return DEMO_ADMIN_EMAIL
    return identifier


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


def reset_all_demo_passwords(session: Session, password: str) -> int:
    """Set ``password`` on every user, leaving ``is_active`` untouched.
    Returns how many accounts changed; one audit entry per account."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"demo password must have at least {MIN_PASSWORD_LENGTH} characters")
    users = session.scalars(select(User).order_by(User.email)).all()
    password_hash = hash_password(password)
    for user in users:
        user.password_hash = password_hash
        write_audit_log(
            session,
            action="demo_password_reset",
            entity_type="security.user",
            actor_identifier="system:startup",
            entity_id=user.id,
            after_state={"password_changed": True, "scope": "all_users"},
        )
    session.commit()
    return len(users)
