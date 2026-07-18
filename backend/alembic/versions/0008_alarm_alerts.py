"""Live Monitor alarm fix (2026-07): extend the previously-unused
`intelligence_alerts` table so it can carry a real, persisted, auditable
alarm raised by the live replay's Compliance/SPC evaluation (CLAUDE.md §23:
triggering data, engine + version, computed inputs, rationale, timestamp).

Adds a direct `characteristic_id` FK (this alert type is always
characteristic-scoped, unlike the existing polymorphic `trigger_id`),
`engine_name`/`engine_version`/`rationale`/`computed_inputs` for the real
engine attribution, and `acknowledged_by_user_id`/`acknowledged_at` for the
"mark read/acknowledged" lifecycle rbac.md already scopes to
`intelligence.alert.update` (viewer/metrologist/quality_engineer/admin).
Also widens `trigger_type`'s CHECK to include the two new alarm rule types.

`intelligence_alerts` has never been written to (no service ever inserted a
row before this fix) -- new columns are added `NOT NULL` directly rather than
nullable+backfill.

Revision ID: 0008_alarm_alerts
Revises: 0007_live_monitor_update_perm
Create Date: 2026-07-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_alarm_alerts"
down_revision = "0007_live_monitor_update_perm"
branch_labels = None
depends_on = None

OLD_TRIGGER_TYPES = ("recommendation", "risk_assessment", "process_event")
NEW_TRIGGER_TYPES = OLD_TRIGGER_TYPES + ("compliance_violation", "capability_below_threshold")


def upgrade() -> None:
    op.add_column(
        "intelligence_alerts",
        sa.Column("characteristic_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column("intelligence_alerts", sa.Column("engine_name", sa.String(length=64), nullable=False))
    op.add_column("intelligence_alerts", sa.Column("engine_version", sa.String(length=32), nullable=False))
    op.add_column("intelligence_alerts", sa.Column("rationale", sa.Text(), nullable=False))
    op.add_column(
        "intelligence_alerts",
        sa.Column("computed_inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.add_column(
        "intelligence_alerts",
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "intelligence_alerts", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_foreign_key(
        "fk_intelligence_alerts_characteristic_id_catalog_char_2c3d",
        "intelligence_alerts",
        "catalog_characteristics",
        ["characteristic_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_intelligence_alerts_acknowledged_by_user_id_secur_4e5f",
        "intelligence_alerts",
        "security_users",
        ["acknowledged_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_intelligence_alerts_characteristic_id", "intelligence_alerts", ["characteristic_id"])
    # Dedup lookup for alarm_detection_service: "is there already an open
    # alert for this characteristic + rule?" -- partial index on the open
    # (unacknowledged) subset, the only rows that query ever filters for.
    op.create_index(
        "ix_intelligence_alerts_open_by_characteristic_trigger",
        "intelligence_alerts",
        ["characteristic_id", "trigger_type"],
        postgresql_where=sa.text("acknowledged_at IS NULL"),
    )

    # Postgres has no ALTER CHECK -- drop and recreate with the wider list.
    op.drop_constraint("ck_intelligence_alerts_trigger_type", "intelligence_alerts", type_="check")
    op.create_check_constraint(
        "ck_intelligence_alerts_trigger_type",
        "intelligence_alerts",
        f"trigger_type IN ({', '.join(repr(t) for t in NEW_TRIGGER_TYPES)})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_intelligence_alerts_trigger_type", "intelligence_alerts", type_="check")
    op.create_check_constraint(
        "ck_intelligence_alerts_trigger_type",
        "intelligence_alerts",
        f"trigger_type IN ({', '.join(repr(t) for t in OLD_TRIGGER_TYPES)})",
    )

    op.drop_index("ix_intelligence_alerts_open_by_characteristic_trigger", table_name="intelligence_alerts")
    op.drop_index("ix_intelligence_alerts_characteristic_id", table_name="intelligence_alerts")
    op.drop_constraint(
        "fk_intelligence_alerts_acknowledged_by_user_id_secur_4e5f", "intelligence_alerts", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_intelligence_alerts_characteristic_id_catalog_char_2c3d", "intelligence_alerts", type_="foreignkey"
    )

    op.drop_column("intelligence_alerts", "acknowledged_at")
    op.drop_column("intelligence_alerts", "acknowledged_by_user_id")
    op.drop_column("intelligence_alerts", "computed_inputs")
    op.drop_column("intelligence_alerts", "rationale")
    op.drop_column("intelligence_alerts", "engine_version")
    op.drop_column("intelligence_alerts", "engine_name")
    op.drop_column("intelligence_alerts", "characteristic_id")
