"""F4.2 (MI-22): per-request database session dependency.

Mirrors `seed/db.py`'s resolution order (DATABASE_URL wins, then the discrete
POSTGRES_* vars) so tests can point the app at a disposable PostgreSQL via a
single env var without touching real configuration. No hardcoded credentials
(CLAUDE.md §5)."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        return url
    settings = get_settings()
    return settings.database_url


engine: Engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Session:
    """Yield a session per request; always closed afterwards (CLAUDE.md §5)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
