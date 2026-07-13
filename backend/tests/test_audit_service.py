"""F4.3 (MI-23): app.services.audit_service tests.

Acceptance criteria covered (Notion MI-23):
- Update of a spec-like entity records correct before/after (only changed
  fields).
- The audit entry carries the real actor resolved from the request (via
  ``get_audit_context`` / ``get_current_user``), not a guessed value.
- No unnecessary PII/secrets leak into audit entries.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from app.core.database import SessionLocal
from app.models.security import AuditLog
from app.services.audit_service import (
    AuditContext,
    get_audit_context,
    record_change,
    record_event,
    write_audit_log,
)
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from conftest import DEMO_USERS, KNOWN_PASSWORD


def _user_id(email: str) -> uuid.UUID:
    db = SessionLocal()
    try:
        stmt = sa.text("SELECT id FROM security_users WHERE email = :e")
        return db.execute(stmt, {"e": email}).scalar_one()
    finally:
        db.close()


def _fetch(entry_id: uuid.UUID) -> AuditLog:
    db = SessionLocal()
    try:
        entry = db.get(AuditLog, entry_id)
        assert entry is not None
        return entry
    finally:
        db.close()


def test_record_event_writes_actor_entity_and_ip() -> None:
    db = SessionLocal()
    try:
        context = AuditContext(
            actor_user_id=_user_id(DEMO_USERS["admin"]),
            actor_identifier=DEMO_USERS["admin"],
            ip_address="203.0.113.10",
        )
        entry = record_event(
            db,
            context,
            action="part_number_created",
            entity_type="catalog.part_number",
            entity_id=uuid.uuid4(),
            after={"code": "MI-DEMO-0001"},
        )
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    stored = _fetch(entry_id)
    assert stored.actor_user_id == _user_id(DEMO_USERS["admin"])
    assert stored.actor_identifier == DEMO_USERS["admin"]
    assert stored.ip_address == "203.0.113.10"
    assert stored.action == "part_number_created"
    assert stored.entity_type == "catalog.part_number"
    assert stored.after_state == {"code": "MI-DEMO-0001"}
    assert stored.before_state is None


def test_record_change_captures_only_changed_fields() -> None:
    db = SessionLocal()
    try:
        context = AuditContext(
            actor_user_id=_user_id(DEMO_USERS["quality_engineer"]),
            actor_identifier=DEMO_USERS["quality_engineer"],
            ip_address="203.0.113.20",
        )
        entity_id = uuid.uuid4()
        before = {"nominal": 10.0, "tolerance": 0.2, "unit": "mm"}
        after = {"nominal": 10.0, "tolerance": 0.15, "unit": "mm"}
        entry = record_change(
            db,
            context,
            action="spec_updated",
            entity_type="catalog.characteristic_spec",
            entity_id=entity_id,
            before=before,
            after=after,
        )
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    stored = _fetch(entry_id)
    # Only "tolerance" changed -- "nominal" and "unit" must not be re-stated.
    assert stored.before_state == {"tolerance": 0.2}
    assert stored.after_state == {"tolerance": 0.15}
    assert stored.entity_id == entity_id


def test_record_change_with_no_actual_diff_stores_no_state() -> None:
    db = SessionLocal()
    try:
        context = AuditContext(
            actor_user_id=_user_id(DEMO_USERS["quality_engineer"]),
            actor_identifier=DEMO_USERS["quality_engineer"],
            ip_address=None,
        )
        entry = record_change(
            db,
            context,
            action="spec_updated",
            entity_type="catalog.characteristic_spec",
            entity_id=uuid.uuid4(),
            before={"nominal": 10.0},
            after={"nominal": 10.0},
        )
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    stored = _fetch(entry_id)
    assert stored.before_state is None
    assert stored.after_state is None


def test_record_event_strips_sensitive_keys() -> None:
    db = SessionLocal()
    try:
        context = AuditContext(
            actor_user_id=_user_id(DEMO_USERS["admin"]),
            actor_identifier=DEMO_USERS["admin"],
            ip_address=None,
        )
        entry = record_event(
            db,
            context,
            action="user_created",
            entity_type="security.user",
            entity_id=uuid.uuid4(),
            after={
                "email": "new.user@demo.local",
                "password": "should-not-be-stored",
                "password_hash": "$argon2id$also-not-stored",
            },
        )
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    stored = _fetch(entry_id)
    assert stored.after_state == {"email": "new.user@demo.local"}
    assert "password" not in (stored.after_state or {})
    assert "password_hash" not in (stored.after_state or {})


def test_write_audit_log_low_level_primitive_unaffected() -> None:
    """The pre-F4.3 low-level primitive (used by /auth/* for pre-actor
    events like a failed login) still works and does no key-stripping."""
    db = SessionLocal()
    try:
        entry = write_audit_log(
            db,
            action="login_failed",
            entity_type="auth.login",
            actor_identifier="unknown@demo.local",
            ip_address="203.0.113.30",
        )
        db.commit()
        entry_id = entry.id
    finally:
        db.close()

    stored = _fetch(entry_id)
    assert stored.actor_user_id is None
    assert stored.actor_identifier == "unknown@demo.local"
    assert stored.action == "login_failed"


def _app_with_whoami() -> FastAPI:
    """A minimal app exposing /whoami (via get_audit_context) plus the real
    /auth router, wired the same way app.main does (limiter + auth router)."""
    from app.api.v1.auth import router as auth_router
    from app.core.ratelimit import limiter

    app = FastAPI()
    app.state.limiter = limiter

    @app.get("/whoami")
    def whoami(context: AuditContext = Depends(get_audit_context)) -> dict:
        return {
            "actor_user_id": str(context.actor_user_id),
            "actor_identifier": context.actor_identifier,
            "ip_address": context.ip_address,
        }

    app.include_router(auth_router)
    return app


def test_get_audit_context_resolves_real_actor_and_ip() -> None:
    """``get_audit_context`` must resolve the actor from the authenticated
    request (JWT), not from a value the endpoint made up."""
    client = TestClient(_app_with_whoami())

    login = client.post(
        "/auth/login",
        data={"username": DEMO_USERS["metrologist"], "password": KNOWN_PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    response = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["actor_user_id"] == str(_user_id(DEMO_USERS["metrologist"]))
    assert body["actor_identifier"] == DEMO_USERS["metrologist"]
    assert body["ip_address"] is not None


def test_get_audit_context_requires_authentication() -> None:
    app = FastAPI()

    @app.get("/whoami")
    def whoami(context: AuditContext = Depends(get_audit_context)) -> dict:
        return {"actor_identifier": context.actor_identifier}

    client = TestClient(app)
    response = client.get("/whoami")
    assert response.status_code == 401
