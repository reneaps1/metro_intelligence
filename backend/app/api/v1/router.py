"""Aggregates every /api/v1 router into one. F4.2+ include their routers
here (`api_router.include_router(...)`); F4.1 ships the empty mount point
so the prefix and auth-dependency wiring exist before any endpoint does."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.intelligence import router as intelligence_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(intelligence_router)
