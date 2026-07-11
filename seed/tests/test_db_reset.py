from __future__ import annotations

import os
import uuid

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

from pathlib import Path  # noqa: E402

from seed.db import get_engine, reset_database  # noqa: E402

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)
def test_reset_is_idempotent_and_leaves_no_residue() -> None:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL  # seed.db.database_url() reads this

    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = get_engine()
    try:
        alembic_command.upgrade(cfg, "head")

        with engine.begin() as connection:
            org_id = uuid.uuid4()
            connection.execute(
                sa.text("INSERT INTO org_organizations (id, code, name) VALUES (:id, 'MI-DEMO-ORG', 'Demo org')"),
                {"id": org_id},
            )

        reset_database(engine)  # first reset: should remove the row above
        reset_database(engine)  # second reset: must be a no-op, not an error

        with engine.begin() as connection:
            count = connection.execute(sa.text("SELECT count(*) FROM org_organizations")).scalar_one()
            assert count == 0
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
