"""Aggregates every /api/v1 router into one. F4.2+ include their routers
here (`api_router.include_router(...)`); F4.1 ships the empty mount point
so the prefix and auth-dependency wiring exist before any endpoint does."""
from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
