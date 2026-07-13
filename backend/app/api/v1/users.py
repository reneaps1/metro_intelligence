"""F4.4 (MI-24): basic admin user management — admin-only per
docs/security/rbac.md's ``security.user``/``security.role`` rows. Password
hashing reuses ``app.core.security.hash_password`` (argon2id); passwords are
never logged, returned, or included in audit before/after state
(``app.services.audit_service`` strips them regardless)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_permission
from app.models.security import Role, User, UserRole
from app.schemas.catalog import Page
from app.schemas.users import RoleRead, UserCreate, UserRead, UserUpdate
from app.services.audit_service import AuditContext, get_audit_context, record_change, record_event

router = APIRouter(tags=["users"])


def _user_read(user: User) -> UserRead:
    return UserRead.model_validate(
        {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "roles": sorted(ur.role.name for ur in user.roles),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
    )


def _resolve_roles(db: Session, role_names: list[str]) -> list[Role]:
    roles = list(db.execute(select(Role).where(Role.name.in_(role_names))).scalars().all())
    found = {role.name for role in roles}
    missing = set(role_names) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown role(s): {', '.join(sorted(missing))}",
        )
    return roles


@router.get("/users", response_model=Page[UserRead])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security.user", "read")),
) -> Page[UserRead]:
    stmt = select(User).order_by(User.email)
    total = db.execute(select(func.count()).select_from(User)).scalar_one()
    rows = db.execute(stmt.limit(page_size).offset((page - 1) * page_size)).scalars().all()
    return Page(
        items=[_user_read(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security.user", "create")),
    context: AuditContext = Depends(get_audit_context),
) -> UserRead:
    roles = _resolve_roles(db, payload.role_names)
    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A user with this email already exists.",
        ) from exc

    for role in roles:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()

    record_event(
        db,
        context,
        action="create",
        entity_type="security.user",
        entity_id=user.id,
        after={
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "roles": sorted(role.name for role in roles),
        },
    )
    db.commit()
    db.refresh(user)
    return _user_read(user)


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security.user", "read")),
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _user_read(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security.user", "update")),
    context: AuditContext = Depends(get_audit_context),
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    before = {
        "display_name": user.display_name,
        "is_active": user.is_active,
        "roles": sorted(ur.role.name for ur in user.roles),
    }

    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role_names is not None:
        roles = _resolve_roles(db, payload.role_names)
        for user_role in list(user.roles):
            db.delete(user_role)
        db.flush()
        for role in roles:
            db.add(UserRole(user_id=user.id, role_id=role.id))
    db.flush()
    db.refresh(user)

    after = {
        "display_name": user.display_name,
        "is_active": user.is_active,
        "roles": sorted(ur.role.name for ur in user.roles),
    }
    record_change(
        db,
        context,
        action="update",
        entity_type="security.user",
        entity_id=user.id,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(user)
    return _user_read(user)


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security.role", "read")),
) -> list[Role]:
    return list(db.execute(select(Role).order_by(Role.name)).scalars().all())
