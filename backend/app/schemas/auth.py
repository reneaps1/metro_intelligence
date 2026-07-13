"""F4.2 (MI-22): request/response schemas for the /auth router."""

from __future__ import annotations

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserMe(BaseModel):
    id: str
    email: str
    display_name: str
    is_active: bool
    roles: list[str]

    model_config = {"from_attributes": True}
