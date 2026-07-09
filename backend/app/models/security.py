from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid7


class User(Base):
    __tablename__ = "security_users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    roles: Mapped[list[UserRole]] = relationship(back_populates="user")
    audit_entries: Mapped[list[AuditLog]] = relationship(back_populates="actor")


class Role(Base):
    __tablename__ = "security_roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    users: Mapped[list[UserRole]] = relationship(back_populates="role")
    permissions: Mapped[list[RolePermission]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "security_permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    token: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    roles: Mapped[list[RolePermission]] = relationship(back_populates="permission")


class UserRole(Base):
    __tablename__ = "security_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_security_user_roles_user_id_role_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_roles.id", ondelete="CASCADE"), primary_key=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="roles")
    role: Mapped[Role] = relationship(back_populates="users")


class RolePermission(Base):
    __tablename__ = "security_role_permissions"
    __table_args__ = (
        UniqueConstraint(
            "role_id",
            "permission_id",
            name="uq_security_role_permissions_role_id_permission_id",
        ),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("security_permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="roles")


class AuditLog(Base):
    __tablename__ = "security_audit_log"
    __table_args__ = (
        Index("ix_security_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_security_audit_log_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True
    )
    actor_identifier: Mapped[str | None] = mapped_column(String(320), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor: Mapped[User | None] = relationship(back_populates="audit_entries")
