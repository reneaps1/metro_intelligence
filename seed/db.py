from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

# backend/ isn't installed as a package — make `app.models` importable the
# same way backend/alembic/env.py does.
BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def database_url() -> str:
    """Mirrors backend/alembic/env.py's resolution order: DATABASE_URL, then
    discrete POSTGRES_* vars. Never a hardcoded connection string (CLAUDE.md §5)."""
    if url := os.getenv("DATABASE_URL"):
        return url

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    if all([host, port, db, user, password]):
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    raise RuntimeError(
        "Set DATABASE_URL or POSTGRES_HOST/POSTGRES_PORT/POSTGRES_DB/"
        "POSTGRES_USER/POSTGRES_PASSWORD before running the seed CLI."
    )


def get_engine() -> Engine:
    return create_engine(database_url())


def get_session(engine: Engine) -> Session:
    return Session(bind=engine)


def reset_database(engine: Engine) -> None:
    """Empty every domain table, keeping users, roles, permissions and the
    audit log (ADR-004). Roles and permissions come from migrations, so
    wiping them broke the demo users generator; the shared purge in
    app.services.domain_purge keeps them. Row-level BEFORE DELETE triggers do
    not fire on TRUNCATE, so append-only domain tables are emptied too; this
    is an environment reset, not an application code path."""
    from app.services.domain_purge import truncate_domain_tables

    with engine.begin() as connection:
        truncate_domain_tables(connection)
