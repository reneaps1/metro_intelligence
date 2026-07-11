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
    """Wipes every table the app models declare, in one statement so
    TRUNCATE ... CASCADE handles FK ordering automatically. Row-level
    BEFORE DELETE triggers (the insert-only guards on measurement_results,
    intelligence_decisions, intelligence_action_taken, security_audit_log)
    do NOT fire on TRUNCATE in PostgreSQL, so this cleanly wipes append-only
    tables too — this is a full environment reset, not an application code path."""
    from app.models import Base

    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
