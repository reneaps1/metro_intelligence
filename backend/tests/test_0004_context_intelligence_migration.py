from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

alembic_command = pytest.importorskip("alembic.command")
alembic_config = pytest.importorskip("alembic.config")
sa = pytest.importorskip("sqlalchemy")

TEST_DATABASE_URL = os.getenv("METRO_TEST_DATABASE_URL")
BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set METRO_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)
def test_context_intelligence_migration_constraints() -> None:
    cfg = alembic_config.Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    engine = sa.create_engine(TEST_DATABASE_URL)

    try:
        alembic_command.upgrade(cfg, "head")

        with engine.begin() as connection:
            # --- catalog + security fixtures ---
            family_id = uuid.uuid4()
            part_id = uuid.uuid4()
            classification_id = uuid.uuid4()
            characteristic_id = uuid.uuid4()
            user_id = uuid.uuid4()

            connection.execute(
                sa.text(
                    "INSERT INTO catalog_product_families (id, code, name) VALUES (:id, 'MI-DEMO-FAM-002', 'Demo family')"
                ),
                {"id": family_id},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO catalog_part_numbers (id, product_family_id, code, name) "
                    "VALUES (:id, :family_id, 'MI-DEMO-PN-002', 'Demo part')"
                ),
                {"id": part_id, "family_id": family_id},
            )
            connection.execute(
                sa.text("INSERT INTO catalog_characteristic_classifications (id, code, name) VALUES (:id, 'significant', 'Significant')"),
                {"id": classification_id},
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO catalog_characteristics (
                        id, part_number_id, balloon_number, name, characteristic_type, unit, classification_id
                    )
                    VALUES (:id, :part_id, '1', 'Flatness', 'flatness', 'mm', :classification_id)
                    """
                ),
                {"id": characteristic_id, "part_id": part_id, "classification_id": classification_id},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO security_users (id, email, display_name) VALUES (:id, 'luis.martinez@demo.local', 'Luis Martinez')"
                ),
                {"id": user_id},
            )

            # --- context + intelligence chain ---
            connection.execute(
                sa.text(
                    "INSERT INTO context_process_events (id, event_type, occurred_at, description) "
                    "VALUES (:id, 'tool_change', now(), 'Tool change on CMM-01')"
                ),
                {"id": uuid.uuid4()},
            )

            risk_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO intelligence_risk_assessments (
                        id, characteristic_id, score, level, factors, engine_name, engine_version
                    )
                    VALUES (:id, :characteristic_id, 72, 'high', '{}'::jsonb, 'risk-engine', '0.1.0')
                    """
                ),
                {"id": risk_id, "characteristic_id": characteristic_id},
            )

            rec_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO intelligence_recommendations (
                        id, characteristic_id, risk_assessment_id, recommendation_type,
                        rationale, evidence, engine_name, engine_version
                    )
                    VALUES (
                        :id, :characteristic_id, :risk_id, 'investigate_cause',
                        'Sustained drift toward upper limit.', '{}'::jsonb, 'rec-engine', '0.1.0'
                    )
                    """
                ),
                {"id": rec_id, "characteristic_id": characteristic_id, "risk_id": risk_id},
            )

            # Cannot accept a recommendation without a decision.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("UPDATE intelligence_recommendations SET state = 'accepted' WHERE id = :id"),
                    {"id": rec_id},
                )
            savepoint.rollback()

            decision_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO intelligence_decisions (id, recommendation_id, decided_by_user_id, action, comment)
                    VALUES (:id, :rec_id, :user_id, 'accepted', 'Confirmed drift, approving investigation.')
                    """
                ),
                {"id": decision_id, "rec_id": rec_id, "user_id": user_id},
            )

            # Now the transition succeeds.
            connection.execute(
                sa.text("UPDATE intelligence_recommendations SET state = 'accepted' WHERE id = :id"),
                {"id": rec_id},
            )

            # Terminal state: cannot transition again.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("UPDATE intelligence_recommendations SET state = 'rejected' WHERE id = :id"),
                    {"id": rec_id},
                )
            savepoint.rollback()

            # Decisions are append-only.
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("UPDATE intelligence_decisions SET comment = 'changed' WHERE id = :id"),
                    {"id": decision_id},
                )
            savepoint.rollback()

            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(sa.text("DELETE FROM intelligence_decisions WHERE id = :id"), {"id": decision_id})
            savepoint.rollback()

            # Action taken: insert succeeds, then append-only holds too.
            action_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    "INSERT INTO intelligence_action_taken (id, decision_id, description) "
                    "VALUES (:id, :decision_id, 'Adjusted fixture, re-measured next batch.')"
                ),
                {"id": action_id, "decision_id": decision_id},
            )
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text("UPDATE intelligence_action_taken SET outcome_status = 'effective' WHERE id = :id"),
                    {"id": action_id},
                )
            savepoint.rollback()

            # inspection_frequency -> decision FK (closed loop from 0002).
            plan_id = uuid.uuid4()
            connection.execute(
                sa.text("INSERT INTO catalog_inspection_plans (id, part_number_id, name) VALUES (:id, :part_id, 'Default plan')"),
                {"id": plan_id, "part_id": part_id},
            )
            connection.execute(
                sa.text(
                    """
                    INSERT INTO catalog_inspection_frequencies (
                        id, inspection_plan_id, characteristic_id, frequency_type, frequency_value, decision_id
                    )
                    VALUES (:id, :plan_id, :characteristic_id, 'every_nth_part', 5, :decision_id)
                    """
                ),
                {"id": uuid.uuid4(), "plan_id": plan_id, "characteristic_id": characteristic_id, "decision_id": decision_id},
            )

            # Different plan so this doesn't collide with the active-frequency
            # unique constraint above — isolates the decision_id FK check.
            other_plan_id = uuid.uuid4()
            connection.execute(
                sa.text("INSERT INTO catalog_inspection_plans (id, part_number_id, name) VALUES (:id, :part_id, 'Bogus test plan')"),
                {"id": other_plan_id, "part_id": part_id},
            )
            savepoint = connection.begin_nested()
            with pytest.raises(sa.exc.DBAPIError):
                connection.execute(
                    sa.text(
                        """
                        INSERT INTO catalog_inspection_frequencies (
                            id, inspection_plan_id, characteristic_id, frequency_type, frequency_value, decision_id
                        )
                        VALUES (:id, :plan_id, :characteristic_id, 'every_nth_part', 3, :bogus_decision_id)
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "plan_id": other_plan_id,
                        "characteristic_id": characteristic_id,
                        "bogus_decision_id": uuid.uuid4(),
                    },
                )
            savepoint.rollback()

            # Alerts are mutable (delivery/read state), unlike decisions/action_taken.
            alert_id = uuid.uuid4()
            connection.execute(
                sa.text(
                    """
                    INSERT INTO intelligence_alerts (id, severity, target_roles, trigger_type, trigger_id, message)
                    VALUES (:id, 'warning', ARRAY['quality_engineer']::text[], 'recommendation', :rec_id, 'New recommendation pending review.')
                    """
                ),
                {"id": alert_id, "rec_id": rec_id},
            )
            connection.execute(
                sa.text("UPDATE intelligence_alerts SET read_at = now() WHERE id = :id"),
                {"id": alert_id},
            )
    finally:
        engine.dispose()
        alembic_command.downgrade(cfg, "base")
