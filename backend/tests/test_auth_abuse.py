"""F4.2 (MI-22): explicit abuse / security test suite.

Covers the acceptance criteria that a static matrix can't:
- Forged and expired JWTs are rejected (401).
- Wrong passwords and non-existent users are rejected (401, no enumeration).
- Brute force: the 6th consecutive failed login locks the account (429) and
  writes an audit entry; a correct password is also refused while locked.
- Rate limiting on /auth/* (slowapi) returns 429 past the limit.
- Refresh-token revocation on logout: a logged-out refresh token is rejected.
- Privilege escalation is blocked: a lower-privilege role cannot reach an
  admin-only endpoint.
- Passwords are stored as argon2id hashes (no plaintext / weak scheme).
"""

from __future__ import annotations

import time
import uuid

import jwt
import sqlalchemy as sa
from app.core.config import get_settings
from app.core.database import SessionLocal

from conftest import DEMO_USERS, KNOWN_PASSWORD

settings = get_settings()


def _user_id(email: str) -> uuid.UUID:
    db = SessionLocal()
    try:
        return db.execute(
            sa.text("SELECT id FROM security_users WHERE email = :e"), {"e": email}
        ).scalar_one()
    finally:
        db.close()


def _audit_count(action: str, identifier: str) -> int:
    db = SessionLocal()
    try:
        return db.execute(
            sa.text("SELECT count(*) FROM security_audit_log " "WHERE action = :a AND actor_identifier = :i"),
            {"a": action, "i": identifier},
        ).scalar_one()
    finally:
        db.close()


def test_forged_jwt_rejected(client):
    forged = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "jti": "forged",
            "type": "access",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        },
        "not-the-real-secret",
        algorithm="HS256",
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_expired_jwt_rejected(client):
    expired = jwt.encode(
        {
            "sub": str(_user_id(DEMO_USERS["admin"])),
            "jti": "expired",
            "type": "access",
            "iat": int(time.time()) - 120,
            "exp": int(time.time()) - 60,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401


def test_wrong_password_rejected(client):
    response = client.post(
        "/auth/login",
        data={"username": DEMO_USERS["admin"], "password": "definitely-wrong"},
    )
    assert response.status_code == 401


def test_nonexistent_user_rejected_same_as_wrong_password(client):
    response = client.post(
        "/auth/login",
        data={"username": "ghost@demo.local", "password": "whatever"},
    )
    assert response.status_code == 401


def test_lockout_after_six_failures_and_audit(client):
    email = DEMO_USERS["quality_engineer"]
    before = _audit_count("login_locked", email)

    # First five failures: still 401 (allowed to keep trying).
    for i in range(5):
        resp = client.post("/auth/login", data={"username": email, "password": "wrong"})
        assert resp.status_code == 401, f"attempt {i + 1} should be 401"

    # Sixth failure: account locks.
    resp = client.post("/auth/login", data={"username": email, "password": "wrong"})
    assert resp.status_code == 429
    assert _audit_count("login_locked", email) == before + 1

    # Even the correct password is refused while locked.
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": KNOWN_PASSWORD},
    )
    assert resp.status_code == 429


def test_rate_limit_on_refresh(client):
    from app.core.ratelimit import limiter

    limiter.reset()
    statuses = []
    for _ in range(70):
        resp = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
        statuses.append(resp.status_code)
    # Earlier attempts are rate-limited-independent (invalid token -> 401),
    # later ones cross the per-route limit -> 429.
    assert 429 in statuses
    assert statuses[0] != 429
    limiter.reset()


def test_logout_revokes_refresh_token(client):
    login = client.post(
        "/auth/login",
        data={"username": DEMO_USERS["metrologist"], "password": KNOWN_PASSWORD},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    # Refresh works before logout.
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200

    # Logout revokes the refresh token.
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = client.post("/auth/logout", headers=headers, json={"refresh_token": refresh_token})
    assert resp.status_code == 204

    # Refresh after logout is rejected.
    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


def test_privilege_escalation_blocked(client, role_tokens):
    # metrologist cannot reach an admin-only endpoint (security.user.administer).
    headers = {"Authorization": f"Bearer {role_tokens('metrologist')}"}
    resp = client.get("/perm/security.user/administer", headers=headers)
    assert resp.status_code == 403

    # admin can.
    admin_headers = {"Authorization": f"Bearer {role_tokens('admin')}"}
    resp = client.get("/perm/security.user/administer", headers=admin_headers)
    assert resp.status_code == 200


def test_passwords_stored_as_argon2id(client):
    db = SessionLocal()
    try:
        h = db.execute(
            sa.text("SELECT password_hash FROM security_users WHERE email = :e"),
            {"e": DEMO_USERS["viewer"]},
        ).scalar_one()
    finally:
        db.close()
    assert h.startswith("$argon2id$")
