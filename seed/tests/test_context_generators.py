from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

from seed.config import load_config  # noqa: E402
from seed.db import get_session  # noqa: E402
from seed.generators.base import SeedContext, make_rng  # noqa: E402
from seed.generators.catalog import generate_catalog  # noqa: E402
from seed.generators.decisions import generate_decision_history  # noqa: E402
from seed.generators.events import generate_process_events  # noqa: E402
from seed.generators.measurements import generate_measurement_series  # noqa: E402
from seed.generators.users import generate_demo_users  # noqa: E402

# seed.db (imported above) inserts backend/ onto sys.path as a side effect,
# the same way seed/generators/users.py reaches app.core.security.
from app.core.security import verify_password  # noqa: E402

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)
def test_context_generators_satisfy_acceptance_criteria(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEED_DEMO_USER_PASSWORD", "demo-password-for-tests-only")

    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)
    try:
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
            raise

        with engine.begin() as connection:
            # One demo user per RBAC role, all on the fictitious .local domain.
            role_counts = connection.execute(
                sa.text(
                    """
                    SELECT r.name, count(*) FROM security_users u
                    JOIN security_user_roles ur ON ur.user_id = u.id
                    JOIN security_roles r ON r.id = ur.role_id
                    GROUP BY r.name
                    """
                )
            ).all()
            assert {name: count for name, count in role_counts} == {
                "viewer": 1,
                "metrologist": 1,
                "quality_engineer": 1,
                "admin": 1,
                "auditor": 1,
            }
            emails = connection.execute(sa.text("SELECT email FROM security_users")).scalars().all()
            assert all(email.endswith("@demo.local") for email in emails)
            # Every demo user can sign in with SEED_DEMO_USER_PASSWORD through
            # the real F4.2 /auth/login flow (argon2id, via app.core.security).
            password_hashes = connection.execute(sa.text("SELECT password_hash FROM security_users")).scalars().all()
            assert all(value is not None for value in password_hashes)
            assert all(verify_password("demo-password-for-tests-only", value) for value in password_hashes)
            assert not verify_password("wrong-password", password_hashes[0])

            # ~20 process events over the 90-day window.
            event_count = connection.execute(sa.text("SELECT count(*) FROM context_process_events")).scalar_one()
            assert 15 <= event_count <= 25

            # Every tool_change event correlated with a shift_after_event
            # characteristic lands within ±2h of the real jump day F3.3 used.
            start_day = context.artifacts["history_start_day"]
            shift_day = start_day + timedelta(days=45)
            tool_change_timestamps = (
                connection.execute(
                    sa.text("SELECT occurred_at FROM context_process_events WHERE event_type = 'tool_change'")
                )
                .scalars()
                .all()
            )
            assert tool_change_timestamps  # at least one correlated event exists
            for occurred_at in tool_change_timestamps:
                assert abs((occurred_at - shift_day).total_seconds()) <= 2 * 3600

            # Recommendation history: ~10 records, states include pending,
            # accepted, and rejected (Decision Memory isn't empty).
            state_counts = connection.execute(
                sa.text("SELECT state, count(*) FROM intelligence_recommendations GROUP BY state")
            ).all()
            states = {state: count for state, count in state_counts}
            assert 8 <= sum(states.values()) <= 12
            assert states.get("accepted", 0) >= 1
            assert states.get("rejected", 0) >= 1
            assert states.get("pending", 0) >= 1

            # No accepted/rejected recommendation lacks a matching Decision —
            # the state machine (migration 0004's trigger) held throughout.
            orphans = connection.execute(
                sa.text(
                    """
                    SELECT count(*) FROM intelligence_recommendations r
                    WHERE r.state IN ('accepted', 'rejected')
                      AND NOT EXISTS (
                          SELECT 1 FROM intelligence_decisions d
                          WHERE d.recommendation_id = r.id AND d.action = r.state
                      )
                    """
                )
            ).scalar_one()
            assert orphans == 0

        # Defense-in-depth: the trigger itself must still reject a direct
        # state flip with no Decision, independent of generator behavior.
        with engine.begin() as connection:
            pending_id = connection.execute(
                sa.text("SELECT id FROM intelligence_recommendations WHERE state = 'pending' LIMIT 1")
            ).scalar_one()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("UPDATE intelligence_recommendations SET state = 'accepted' WHERE id = :id"),
                    {"id": pending_id},
                )
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
