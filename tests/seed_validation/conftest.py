"""F3.5 (MI-20): shared fixtures for the seed validation suite.

`seeded_engine` runs the full generator pipeline (catalog -> measurements ->
users -> process events -> decision history, in the same order
`seed/__main__.py` registers them) against a disposable PostgreSQL database
exactly once per test session, so test_constraints.py and
test_statistics.py can both assert against the same generated dataset
without re-running the (slow) generation step per test module -- that's
what keeps the whole suite inside the "<2 minutes in CI" acceptance
criterion (docs/tasks/F3.5.md).

Every test that needs a database is skipped, not failed, when
METRO_TEST_DATABASE_URL isn't set (mirrors seed/tests/ and backend/tests/)
so `pytest tests/seed_validation` still runs cleanly on a laptop with no
Postgres available -- only the confidentiality lint (test_confidentiality.py)
needs no database at all.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

# Defensive: make `seed.*` and `app.*` importable regardless of how pytest's
# rootdir insertion resolves for this package (tests/ has no __init__.py,
# unlike seed/tests/), mirroring seed/db.py's own sys.path setup.
for path in (REPO_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")

requires_database = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)


@pytest.fixture(scope="session")
def seeded_engine():
    if not TEST_DATABASE_URL:
        pytest.skip("Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.")

    os.environ.setdefault("SEED_DEMO_USER_PASSWORD", "demo-password-for-tests-only")

    from seed.config import load_config
    from seed.db import get_session
    from seed.generators.base import SeedContext, make_rng
    from seed.generators.catalog import generate_catalog
    from seed.generators.decisions import generate_decision_history
    from seed.generators.events import generate_process_events
    from seed.generators.measurements import generate_measurement_series
    from seed.generators.users import generate_demo_users

    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)
    alembic_command.upgrade(cfg, "head")

    session = get_session(engine)
    context = SeedContext(session=session, rng=make_rng(20260709), config=load_config())
    try:
        generate_catalog(context)
        generate_measurement_series(context)
        generate_demo_users(context)
        generate_process_events(context)
        generate_decision_history(context)
        session.commit()
    except Exception:
        session.rollback()
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
        raise
    finally:
        session.close()

    yield engine, context

    engine.dispose()
    alembic_command.downgrade(cfg, "base")
