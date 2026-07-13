"""F4.4 (MI-24): request/response schemas for basic admin user management.

``email`` is validated with a plain shape check rather than pydantic's
``EmailStr``: ``email-validator``'s default deliverability rules reject
reserved/special-use TLDs, which would reject every fictitious
``@demo.local`` account this platform's own demo policy requires
(CLAUDE.md §7/§20, docs/seed-data-strategy.md)."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

_EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=255)
    role_names: list[str] = Field(min_length=1)
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def _valid_email_shape(cls, value: str) -> str:
        if not _EMAIL_SHAPE.match(value):
            raise ValueError("Must be a valid email address.")
        return value


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    role_names: list[str] | None = Field(default=None, min_length=1)


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    is_system: bool

    model_config = {"from_attributes": True}
