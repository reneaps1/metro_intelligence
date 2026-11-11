"""Operator recovery of the demo administrator (IQ-F30)."""

from __future__ import annotations

import pytest
from app.core.database import SessionLocal
from app.core.password import verify_password
from app.models import AuditLog, User
from app.services.demo_admin import reset_demo_admin
from sqlalchemy import select

from conftest import DEMO_USERS


def test_reset_changes_password_reactivates_and_audits(auth_database: None) -> None:
    email = DEMO_USERS["auditor"]
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        assert user is not None
        original_hash, original_active = user.password_hash, user.is_active
        user.is_active = False
        session.commit()
        try:
            assert reset_demo_admin(session, email, "Nueva-clave-segura-1") is True
            session.refresh(user)
            assert user.is_active is True
            assert verify_password("Nueva-clave-segura-1", user.password_hash)
            log = session.scalars(
                select(AuditLog).where(AuditLog.action == "demo_admin_reset", AuditLog.entity_id == user.id)
            ).first()
            assert log is not None and "Nueva" not in str(log.after_state)
        finally:
            user.password_hash, user.is_active = original_hash, original_active
            session.commit()


def test_reset_refuses_short_passwords_and_unknown_users(auth_database: None) -> None:
    with SessionLocal() as session:
        with pytest.raises(ValueError):
            reset_demo_admin(session, DEMO_USERS["auditor"], "corta")
        assert reset_demo_admin(session, "nadie@demo.local", "Nueva-clave-segura-1") is False
