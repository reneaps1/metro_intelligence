"""Create context + intelligence schema: process events, risk assessments,
recommendations, decisions, action taken, and alerts. Closes the deferred
inspection_frequency -> decision FK opened in 0002.

Revision ID: 0004_context_intelligence
Revises: 0003_measurement
Create Date: 2026-07-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_context_intelligence"
down_revision = "0003_measurement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_process_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["line_id"], ["org_lines.id"], ondelete="SET NULL", name="fk_context_process_events_line_id_org_lines"),
        sa.ForeignKeyConstraint(["machine_id"], ["org_machines.id"], ondelete="SET NULL", name="fk_context_process_events_machine_id_org_machines"),
        sa.CheckConstraint(
            "event_type IN ('tool_change', 'maintenance', 'material_lot_change', 'machine_adjustment')",
            name="ck_context_process_events_event_type",
        ),
    )
    op.create_index("ix_context_process_events_occurred_at", "context_process_events", ["occurred_at"])

    op.create_table(
        "intelligence_risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("characteristic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("engine_name", sa.String(length=64), nullable=False),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["characteristic_id"], ["catalog_characteristics.id"], ondelete="RESTRICT",
            name="fk_intelligence_risk_assessments_characteristic_id_cata_1d2e",
        ),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_intelligence_risk_assessments_score_range"),
        sa.CheckConstraint("level IN ('low', 'medium', 'high', 'critical')", name="ck_intelligence_risk_assessments_level"),
    )
    op.create_index("ix_intelligence_risk_assessments_characteristic_id", "intelligence_risk_assessments", ["characteristic_id", "computed_at"])

    op.create_table(
        "intelligence_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("characteristic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_assessment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommendation_type", sa.String(length=32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("engine_name", sa.String(length=64), nullable=False),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["characteristic_id"], ["catalog_characteristics.id"], ondelete="RESTRICT",
            name="fk_intelligence_recommendations_characteristic_id_cata_3f4a",
        ),
        sa.ForeignKeyConstraint(
            ["risk_assessment_id"], ["intelligence_risk_assessments.id"], ondelete="SET NULL",
            name="fk_intelligence_recommendations_risk_assessment_id_int_5b6c",
        ),
        sa.CheckConstraint(
            "recommendation_type IN ('frequency_increase', 'frequency_decrease', 'immediate_inspection', 'investigate_cause', 'post_event_validation')",
            name="ck_intelligence_recommendations_type",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'accepted', 'rejected', 'superseded', 'expired')",
            name="ck_intelligence_recommendations_state",
        ),
    )

    op.create_table(
        "intelligence_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["recommendation_id"], ["intelligence_recommendations.id"], ondelete="RESTRICT",
            name="fk_intelligence_decisions_recommendation_id_intelligen_7d8e",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"], ["security_users.id"], ondelete="RESTRICT",
            name="fk_intelligence_decisions_decided_by_user_id_security_users",
        ),
        sa.CheckConstraint("action IN ('accepted', 'rejected')", name="ck_intelligence_decisions_action"),
        sa.UniqueConstraint("recommendation_id", name="uq_intelligence_decisions_recommendation_id"),
    )

    op.create_table(
        "intelligence_action_taken",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("outcome_status", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_id"], ["intelligence_decisions.id"], ondelete="RESTRICT",
            name="fk_intelligence_action_taken_decision_id_intelligence_de_9f0a",
        ),
        sa.CheckConstraint(
            "outcome_status IN ('pending', 'effective', 'ineffective', 'not_applicable')",
            name="ck_intelligence_action_taken_outcome_status",
        ),
    )

    op.create_table(
        "intelligence_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("target_roles", postgresql.ARRAY(sa.String(length=32)), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False),
        sa.Column("trigger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("severity IN ('info', 'warning', 'critical')", name="ck_intelligence_alerts_severity"),
        sa.CheckConstraint(
            "trigger_type IN ('recommendation', 'risk_assessment', 'process_event')",
            name="ck_intelligence_alerts_trigger_type",
        ),
    )
    op.create_index("ix_intelligence_alerts_created_at", "intelligence_alerts", ["created_at"])

    # Close the loop opened in 0002: inspection_frequency changes originating
    # from an accepted recommendation now reference the deciding Decision.
    op.create_foreign_key(
        "fk_catalog_inspection_frequencies_decision_id_intellige_b1c2",
        "catalog_inspection_frequencies",
        "intelligence_decisions",
        ["decision_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Decisions and action_taken are append-only, same pattern as
    # security_audit_log (0001): corrections insert a new row, never mutate.
    op.execute(
        """
        CREATE FUNCTION prevent_intelligence_append_only_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
        END;
        $$;
        """
    )
    for table in ("intelligence_decisions", "intelligence_action_taken"):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_no_update_delete
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION prevent_intelligence_append_only_mutation();
            """
        )
        op.execute(f"REVOKE UPDATE, DELETE ON TABLE {table} FROM PUBLIC")

    # A recommendation's state is a small state machine: pending is the only
    # state that may transition, and only to accepted/rejected/superseded/
    # expired; accepted/rejected additionally require an associated Decision
    # to already exist (CLAUDE.md §24: human review before any effect).
    op.execute(
        """
        CREATE FUNCTION check_recommendation_state_transition()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.state <> 'pending' AND NEW.state IS DISTINCT FROM OLD.state THEN
                RAISE EXCEPTION 'recommendation state % is terminal, cannot transition to %', OLD.state, NEW.state;
            END IF;
            IF NEW.state IN ('accepted', 'rejected') THEN
                IF NOT EXISTS (
                    SELECT 1 FROM intelligence_decisions
                    WHERE recommendation_id = NEW.id AND action = NEW.state
                ) THEN
                    RAISE EXCEPTION 'recommendation cannot transition to % without a matching decision', NEW.state;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_intelligence_recommendations_state_transition
        BEFORE UPDATE ON intelligence_recommendations
        FOR EACH ROW
        WHEN (NEW.state IS DISTINCT FROM OLD.state)
        EXECUTE FUNCTION check_recommendation_state_transition();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_intelligence_recommendations_state_transition ON intelligence_recommendations")
    op.execute("DROP FUNCTION IF EXISTS check_recommendation_state_transition()")
    for table in ("intelligence_decisions", "intelligence_action_taken"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_no_update_delete ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_intelligence_append_only_mutation()")

    op.drop_constraint(
        "fk_catalog_inspection_frequencies_decision_id_intellige_b1c2",
        "catalog_inspection_frequencies",
        type_="foreignkey",
    )

    op.drop_index("ix_intelligence_alerts_created_at", table_name="intelligence_alerts")
    op.drop_table("intelligence_alerts")
    op.drop_table("intelligence_action_taken")
    op.drop_table("intelligence_decisions")
    op.drop_table("intelligence_recommendations")
    op.drop_index("ix_intelligence_risk_assessments_characteristic_id", table_name="intelligence_risk_assessments")
    op.drop_table("intelligence_risk_assessments")
    op.drop_index("ix_context_process_events_occurred_at", table_name="context_process_events")
    op.drop_table("context_process_events")
