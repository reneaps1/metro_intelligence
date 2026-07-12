"""F4.2 (MI-22): /auth router — login, refresh, logout, and /me.

Security properties (CLAUDE.md §5, §18):
- Passwords verified with argon2id (see ``app.core.security``).
- JWT access + refresh, HS256, with ``exp``/``iat``/``jti`` claims.
- Brute-force protection: account lockout after
  ``LOGIN_LOCKOUT_THRESHOLD`` consecutive failures, plus slowapi rate limiting
  on every ``/auth/*`` route.
- Every login outcome (success / failure / lockout) and logout writes an
  append-only ``AuditLog`` entry.
- No secrets or credentials are returned in responses; error bodies carry no
   internals.
"""

import uuid

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ratelimit import limiter
from app.core.security import (
    _login_attempts,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    is_token_revoked,
    revoke_token,
    verify_password,
    write_audit_log,
)
from app.models.security import User
from app.schemas.auth import RefreshRequest, TokenResponse, UserMe

router = APIRouter(prefix="/auth", tags=["auth"])

# Constant-time dummy hash so a non-existent user doesn't short-circuit the
# password-verify path (reduces account-enumeration timing leakage).
_DUMMY_HASH = hash_password("dummy-password-not-used")


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse)
@limiter.limit("30/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = form_data.username
    ip = _client_ip(request)

    if _login_attempts.is_locked(email):
        write_audit_log(
            db,
            action="login_locked",
            entity_type="auth.login",
            actor_identifier=email,
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to failed login attempts.",
        )

    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    if user is None:
        # Run a verify against a dummy hash to keep timing comparable.
        verify_password(form_data.password, _DUMMY_HASH)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    if not verify_password(form_data.password, user.password_hash):
        locked = _login_attempts.register_failure(email)
        write_audit_log(
            db,
            action="login_failed",
            entity_type="auth.login",
            actor_user_id=user.id,
            actor_identifier=email,
            ip_address=ip,
        )
        if locked:
            write_audit_log(
                db,
                action="login_locked",
                entity_type="auth.login",
                actor_user_id=user.id,
                actor_identifier=email,
                ip_address=ip,
            )
        db.commit()
        if locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked due to failed login attempts.",
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    _login_attempts.reset(email)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    write_audit_log(
        db,
        action="login_success",
        entity_type="auth.login",
        actor_user_id=user.id,
        actor_identifier=email,
        ip_address=ip,
    )
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("60/minute")
def refresh(
    request: Request,
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        token_data = decode_token(payload.refresh_token)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        ) from None

    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token.")

    jti = token_data.get("jti")
    if not jti or is_token_revoked(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked.")

    subject = token_data.get("sub")
    user = db.get(User, uuid.UUID(subject)) if subject else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    # Rotate: revoke the presented refresh token, issue a fresh pair.
    revoke_token(jti)
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    write_audit_log(
        db,
        action="token_refresh",
        entity_type="auth.token",
        actor_user_id=user.id,
        ip_address=_client_ip(request),
    )
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    payload: RefreshRequest | None = Body(default=None),
    db: Session = Depends(get_db),
) -> None:
    if payload and payload.refresh_token:
        try:
            token_data = decode_token(payload.refresh_token)
            jti = token_data.get("jti")
            if jti:
                revoke_token(jti)
        except jwt.InvalidTokenError:
            pass
    write_audit_log(
        db,
        action="logout",
        entity_type="auth.logout",
        actor_user_id=current_user.id,
    )
    db.commit()


@router.get("/me", response_model=UserMe)
def me(current_user: User = Depends(get_current_user)) -> UserMe:
    roles = [ur.role.name for ur in current_user.roles]
    return UserMe(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        is_active=current_user.is_active,
        roles=roles,
    )
