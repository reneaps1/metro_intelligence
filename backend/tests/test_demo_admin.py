"""Operator recovery of the demo administrator (IQ-F30)."""

from __future__ import annotations

import pytest
from app.core.database import SessionLocal
from app.core.password import verify_password
from app.models import AuditLog, User
from app.services.demo_admin import reset_all_demo_passwords, reset_demo_admin
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


def test_reset_all_changes_every_password_keeps_activation_and_audits(auth_database: None) -> None:
    new_password = "Otra-clave-segura-2"
    with SessionLocal() as session:
        users = session.scalars(select(User)).all()
        originals = {user.id: (user.password_hash, user.is_active) for user in users}
        inactive = next(user for user in users if user.email == DEMO_USERS["viewer"])
        inactive.is_active = False
        session.commit()
        try:
            with pytest.raises(ValueError):
                reset_all_demo_passwords(session, "corta")  # 5 characters: refused, nothing changes
            session.rollback()
            assert all(session.get(User, uid).password_hash == originals[uid][0] for uid in originals)

            assert reset_all_demo_passwords(session, new_password) == len(users)
            for user in session.scalars(select(User)).all():
                assert verify_password(new_password, user.password_hash)
            session.refresh(inactive)
            assert inactive.is_active is False  # a disabled account stays disabled
            logs = session.scalars(select(AuditLog).where(AuditLog.action == "demo_password_reset")).all()
            assert {log.entity_id for log in logs} >= set(originals)
            assert all("Otra" not in str(log.after_state) for log in logs)
        finally:
            for user in session.scalars(select(User)).all():
                user.password_hash, user.is_active = originals[user.id]
            session.commit()


def test_login_alias_signs_in_the_demo_administrator(client, monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.demo_admin as demo_admin

    from conftest import KNOWN_PASSWORD

    def login(username: str, password: str):
        return client.post("/auth/login", data={"username": username, "password": password})

    monkeypatch.setattr(demo_admin, "DEMO_ADMIN_EMAIL", DEMO_USERS["admin"])

    # Not configured: the short name is just an unknown user.
    monkeypatch.delenv("SEED_DEMO_USER_LOGIN_ALIAS", raising=False)
    assert login("admin", KNOWN_PASSWORD).status_code == 401

    monkeypatch.setenv("SEED_DEMO_USER_LOGIN_ALIAS", "admin")
    response = login(" Admin ", KNOWN_PASSWORD)
    assert response.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.json()["email"] == DEMO_USERS["admin"]
    # Same account, so the same password check and the email still work.
    assert login("admin", "wrong").status_code == 401
    assert login(DEMO_USERS["admin"], KNOWN_PASSWORD).status_code == 200


def test_login_alias_is_ignored_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.demo_admin as demo_admin

    monkeypatch.setenv("SEED_DEMO_USER_LOGIN_ALIAS", "admin")
    assert demo_admin.resolve_login_alias("admin") == demo_admin.DEMO_ADMIN_EMAIL
    assert demo_admin.resolve_login_alias("otro@demo.local") == "otro@demo.local"
    monkeypatch.setattr(demo_admin, "get_settings", lambda: type("S", (), {"app_env": "production"})())
    assert demo_admin.resolve_login_alias("admin") == "admin"
