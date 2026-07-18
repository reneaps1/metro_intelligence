"""F4.2 (MI-22): JWT issuing/verification, argon2id password hashing, and the
RBAC ``require_permission`` FastAPI dependency (deny-by-default, per
docs/security/rbac.md).

Design rules (CLAUDE.md §5, §18):
- No hardcoded secrets: the JWT signing key comes from ``settings.jwt_secret``
  (env-injected, documented in ``.env.example``).
- Every dependency fails closed: unauthenticated calls get 401, unauthorized
  calls get 403, and an unknown permission token is denied (there is no
  "allow if not in the matrix" path).
- Refresh tokens can be revoked (logout) via an in-memory jti set; this is a
  demo-grade revocation store (single process) and is explicitly called out as
  such in the PR. A shared/redis-backed store is a post-demo hardening item.
- Login brute-force protection: an in-memory failure counter locks an account
  after ``LOGIN_LOCKOUT_THRESHOLD`` consecutive failures. Same demo-grade
  caveat as the revocation store.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.security import Permission, RolePermission, User, UserRole
from app.core.password import hash_password, verify_password

settings = get_settings()

# --- JWT ----------------------------------------------------------------------
ALGORITHM = settings.jwt_algorithm


def _create_token(*, subject: str, token_type: str, expires_in_seconds: int, jti: str) -> str:
    now = int(time.time())
    payload = {
        "sub": subject,
        "jti": jti,
        "type": token_type,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(
        subject=str(user_id),
        token_type="access",
        expires_in_seconds=settings.access_token_expire_minutes * 60,
        jti=uuid.uuid4().hex,
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_in_seconds=settings.refresh_token_expire_days * 24 * 3600,
        jti=uuid.uuid4().hex,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Raise ``jwt.InvalidTokenError`` (incl. expiry) on any invalid token."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])


# --- Revocation (in-memory, demo-grade) ---------------------------------------
_revoked_jtis: set[str] = set()


def revoke_token(jti: str) -> None:
    _revoked_jtis.add(jti)


def is_token_revoked(jti: str) -> bool:
    return jti in _revoked_jtis


def _reset_revocation_store_for_tests() -> None:
    _revoked_jtis.clear()


# --- Login brute-force lockout (in-memory, demo-grade) ------------------------
LOGIN_LOCKOUT_THRESHOLD = 6
LOGIN_LOCKOUT_SECONDS = 15 * 60


class _LoginAttemptTracker:
    def __init__(self, threshold: int, lock_seconds: int) -> None:
        self._threshold = threshold
        self._lock_seconds = lock_seconds
        self._failures: dict[str, int] = {}
        self._locked_until: dict[str, float] = {}

    def is_locked(self, key: str) -> bool:
        until = self._locked_until.get(key)
        if until is None:
            return False
        if time.monotonic() < until:
            return True
        self._locked_until.pop(key, None)
        self._failures.pop(key, None)
        return False

    def register_failure(self, key: str) -> bool:
        """Return True if this failure crossed the threshold and locked the key."""
        self._failures[key] = self._failures.get(key, 0) + 1
        if self._failures[key] >= self._threshold:
            self._locked_until[key] = time.monotonic() + self._lock_seconds
            return True
        return False

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
        self._locked_until.pop(key, None)

    def clear(self) -> None:
        self._failures.clear()
        self._locked_until.clear()


_login_attempts = _LoginAttemptTracker(LOGIN_LOCKOUT_THRESHOLD, LOGIN_LOCKOUT_SECONDS)


def _reset_login_attempts_for_tests() -> None:
    _login_attempts.clear()


# --- Auth dependencies --------------------------------------------------------
# Audit logging (write_audit_log, record_event, record_change) lives in
# app.services.audit_service (F4.3 / MI-23) -- import from there.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        raise credentials_exc from None

    jti = payload.get("jti")
    if not jti or is_token_revoked(jti):
        raise credentials_exc

    subject = payload.get("sub")
    if not subject:
        raise credentials_exc

    try:
        user = db.get(User, uuid.UUID(subject))
    except (ValueError, TypeError):
        raise credentials_exc from None

    if user is None or not user.is_active:
        raise credentials_exc
    return user


def _user_has_permission(db: Session, user: User, resource: str, action: str) -> bool:
    token = f"{resource}.{action}"
    stmt = (
        select(Permission.token)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id, Permission.token == token)
    )
    return db.execute(stmt).first() is not None


def require_permission(resource: str, action: str) -> Callable[[User, Session], User]:
    """Deny-by-default FastAPI dependency enforcing one RBAC permission token.

    ``resource`` is the matrix key (e.g. ``"catalog.part_number"``) and
    ``action`` one of read/create/update/decide/administer. A token not present
    in the matrix is denied for every role — there is no implicit allow.
    """

    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if _user_has_permission(db, current_user, resource, action):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {resource}.{action}",
        )

    return dependency
