"""Aggregates every /api/v1 router into one. F4.2+ include their routers
here (`api_router.include_router(...)`); F4.1 ships the empty mount point
so the prefix and auth-dependency wiring exist before any endpoint does."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.imports import router as imports_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.measurements import router as measurements_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(users_router)
api_router.include_router(imports_router)
api_router.include_router(measurements_router)
api_router.include_router(intelligence_router)
