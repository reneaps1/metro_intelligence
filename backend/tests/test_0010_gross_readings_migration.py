"""Migration 0010: n_gross on the daily characteristic statistics; clean downgrade."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database."
)


def _n_gross(engine: sa.Engine) -> tuple[str, str | None] | None:
    """(is_nullable, column_default) of n_gross, or None when the column is absent."""
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT is_nullable, column_default FROM information_schema.columns "
                "WHERE table_name = 'process_characteristic_daily' AND column_name = 'n_gross'"
            )
        ).one_or_none()
    return None if row is None else (row[0], row[1])


def test_gross_readings_migration_upgrade_and_downgrade() -> None:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    engine = sa.create_engine(TEST_DATABASE_URL)
    try:
        # Whatever revision the database starts at, go up, down one, and up again.
        alembic_command.upgrade(cfg, "head")
        assert _n_gross(engine) == ("NO", "0")

        alembic_command.downgrade(cfg, "0009_process_model")
        assert _n_gross(engine) is None

        alembic_command.upgrade(cfg, "head")
        assert _n_gross(engine) == ("NO", "0")
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
