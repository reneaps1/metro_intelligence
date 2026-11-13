"""Process model (ADR-005): operations, recipes, part instances, per-step
results and derived daily statistics. Extends measurement_results with the
station's own verdict, makes specification_id optional (values without a
specification), widens value/deviation precision, adds a sample index and
monthly partitions for 2025 and 2027, and adds the `process.operation.read`
permission for every role.

The 2025 partitions can only be attached while the DEFAULT partition holds no
2025 rows: run `python -m app.cli.purge_domain_data --confirm` first on a
database that still carries demo data (ADR-004).

Revision ID: 0009_process_model
Revises: 0008_alarm_alerts
Create Date: 2026-11-13
"""

from __future__ import annotations

import secrets
import time
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_process_model"
down_revision = "0008_alarm_alerts"
branch_labels = None
depends_on = None

PERMISSION_TOKEN = "process.operation.read"
GRANTED_ROLES = ["viewer", "metrologist", "quality_engineer", "admin", "auditor"]
NEW_PARTITION_YEARS = (2025, 2027)
UUID = postgresql.UUID(as_uuid=True)


def _uuid7() -> uuid.UUID:
    unix_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    value = (unix_ms << 80) | (0x7 << 76) | (secrets.randbits(12) << 64) | (0b10 << 62) | secrets.randbits(62)
    return uuid.UUID(int=value)


def _created_at() -> sa.Column:
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "process_operations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("line_id", UUID, sa.ForeignKey("org_lines.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("machine_id", UUID, sa.ForeignKey("org_machines.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("operation_kind", sa.String(32), nullable=False),
        sa.Column("side", sa.String(16), nullable=True),
        sa.Column("sequence", sa.SmallInteger, nullable=False),
        _created_at(),
        sa.UniqueConstraint("line_id", "sequence", name="uq_process_operations_line_id_sequence"),
        sa.UniqueConstraint("line_id", "code", name="uq_process_operations_line_id_code"),
        sa.CheckConstraint(
            "operation_kind IN ('electrical', 'pin_length', 'pin_position', 'type_check')",
            name="operation_kind",
        ),
        sa.CheckConstraint("side IS NULL OR side IN ('pcb', 'connector')", name="side"),
    )
    op.create_table(
        "process_recipes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("line_id", UUID, sa.ForeignKey("org_lines.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("code", sa.SmallInteger, nullable=False),
        sa.Column(
            "part_number_id", UUID, sa.ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "variant_part_number_id",
            UUID,
            sa.ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("variant_label", sa.String(255), nullable=True),
        _created_at(),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("line_id", "code", name="uq_process_recipes_line_id_code"),
    )
    op.create_table(
        "process_part_instances",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("line_id", UUID, sa.ForeignKey("org_lines.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("serial_number", sa.String(64), nullable=False),
        sa.Column("recipe_id", UUID, sa.ForeignKey("process_recipes.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        _created_at(),
        sa.UniqueConstraint("line_id", "serial_number", name="uq_process_part_instances_line_id_serial_number"),
    )
    op.create_table(
        "process_step_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "part_instance_id",
            UUID,
            sa.ForeignKey("process_part_instances.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "operation_id", UUID, sa.ForeignKey("process_operations.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column(
            "measurement_sample_id",
            UUID,
            sa.ForeignKey("measurement_samples.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nest", sa.SmallInteger, nullable=True),
        sa.Column("program_number", sa.SmallInteger, nullable=True),
        sa.Column("machine_ok", sa.Boolean, nullable=True),
        sa.Column("error_count", sa.SmallInteger, nullable=True),
        sa.Column("reference_ok", sa.Boolean, nullable=True),
        sa.Column("attempt_no", sa.SmallInteger, nullable=False, server_default="1"),
        sa.UniqueConstraint("measurement_sample_id", name="uq_process_step_results_measurement_sample_id"),
    )
    op.create_index(
        "ix_process_step_results_operation_id_recorded_at", "process_step_results", ["operation_id", "recorded_at"]
    )
    op.create_index("ix_process_step_results_part_instance_id", "process_step_results", ["part_instance_id"])

    op.create_table(
        "process_step_daily",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column(
            "operation_id", UUID, sa.ForeignKey("process_operations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("recipe_id", UUID, sa.ForeignKey("process_recipes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("nest", sa.SmallInteger, nullable=True),
        sa.Column("pieces", sa.Integer, nullable=False),
        sa.Column("pieces_machine_nok", sa.Integer, nullable=False),
        sa.Column("pieces_spec_nok", sa.Integer, nullable=False),
        sa.Column("first_attempt_ok", sa.Integer, nullable=False),
        sa.Column("repeat_attempts", sa.Integer, nullable=False),
    )
    op.create_index("ix_process_step_daily_operation_id_day", "process_step_daily", ["operation_id", "day"])

    op.create_table(
        "process_characteristic_daily",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("day", sa.Date, nullable=False),
        sa.Column(
            "operation_id", UUID, sa.ForeignKey("process_operations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("recipe_id", UUID, sa.ForeignKey("process_recipes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("nest", sa.SmallInteger, nullable=True),
        sa.Column(
            "characteristic_id",
            UUID,
            sa.ForeignKey("catalog_characteristics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "specification_id",
            UUID,
            sa.ForeignKey("catalog_specifications.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("n", sa.Integer, nullable=False),
        sa.Column("n_machine_nok", sa.Integer, nullable=False),
        sa.Column("n_evaluated", sa.Integer, nullable=False),
        sa.Column("n_spec_nok", sa.Integer, nullable=False),
        sa.Column("n_machine_ok_spec_nok", sa.Integer, nullable=False),
        sa.Column("sum_value", sa.Double, nullable=False),
        sa.Column("sum_sq_value", sa.Double, nullable=False),
        sa.Column("min_value", sa.Double, nullable=False),
        sa.Column("max_value", sa.Double, nullable=False),
    )
    op.create_index(
        "ix_process_characteristic_daily_operation_id_day", "process_characteristic_daily", ["operation_id", "day"]
    )
    op.create_index(
        "ix_process_characteristic_daily_characteristic_id_day",
        "process_characteristic_daily",
        ["characteristic_id", "day"],
    )

    op.create_table(
        "process_stats_builds",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("built_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("line_id", UUID, sa.ForeignKey("org_lines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("engine_name", sa.String(64), nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=False),
    )

    # measurement_results: station verdict, optional specification, wider precision.
    op.execute("ALTER TABLE measurement_results ALTER COLUMN specification_id DROP NOT NULL")
    op.execute("ALTER TABLE measurement_results ALTER COLUMN value TYPE NUMERIC(20, 9)")
    op.execute("ALTER TABLE measurement_results ALTER COLUMN deviation TYPE NUMERIC(20, 9)")
    op.execute("ALTER TABLE measurement_results ADD COLUMN machine_ok BOOLEAN")
    op.execute("ALTER TABLE measurement_results ADD COLUMN machine_code SMALLINT")
    op.create_index(
        "ix_measurement_results_measurement_sample_id", "measurement_results", ["measurement_sample_id"]
    )
    for year in NEW_PARTITION_YEARS:
        for month in range(1, 13):
            next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
            op.execute(
                f"""
                CREATE TABLE measurement_results_{year}_{month:02d}
                PARTITION OF measurement_results
                FOR VALUES FROM ('{year}-{month:02d}-01') TO ('{next_year}-{next_month:02d}-01')
                """
            )

    conn = op.get_bind()
    permission_id = _uuid7()
    op.bulk_insert(
        sa.table(
            "security_permissions",
            sa.column("id", UUID),
            sa.column("token", sa.String()),
            sa.column("description", sa.Text()),
        ),
        [{"id": permission_id, "token": PERMISSION_TOKEN, "description": f"Allows {PERMISSION_TOKEN}"}],
    )
    role_ids = conn.execute(
        sa.text("SELECT id FROM security_roles WHERE name = ANY(:names)"), {"names": GRANTED_ROLES}
    ).scalars()
    op.bulk_insert(
        sa.table("security_role_permissions", sa.column("role_id", UUID), sa.column("permission_id", UUID)),
        [{"role_id": role_id, "permission_id": permission_id} for role_id in role_ids],
    )


def downgrade() -> None:
    conn = op.get_bind()
    permission_id = conn.execute(
        sa.text("SELECT id FROM security_permissions WHERE token = :token"), {"token": PERMISSION_TOKEN}
    ).scalar_one_or_none()
    if permission_id is not None:
        conn.execute(
            sa.text("DELETE FROM security_role_permissions WHERE permission_id = :pid"), {"pid": permission_id}
        )
        conn.execute(sa.text("DELETE FROM security_permissions WHERE id = :pid"), {"pid": permission_id})

    for year in NEW_PARTITION_YEARS:
        for month in range(1, 13):
            op.execute(f"DROP TABLE IF EXISTS measurement_results_{year}_{month:02d}")
    op.drop_index("ix_measurement_results_measurement_sample_id", table_name="measurement_results")
    op.execute("ALTER TABLE measurement_results DROP COLUMN machine_code")
    op.execute("ALTER TABLE measurement_results DROP COLUMN machine_ok")
    op.execute("ALTER TABLE measurement_results ALTER COLUMN deviation TYPE NUMERIC(18, 6)")
    op.execute("ALTER TABLE measurement_results ALTER COLUMN value TYPE NUMERIC(18, 6)")
    op.execute("ALTER TABLE measurement_results ALTER COLUMN specification_id SET NOT NULL")

    op.drop_table("process_stats_builds")
    op.drop_table("process_characteristic_daily")
    op.drop_table("process_step_daily")
    op.drop_table("process_step_results")
    op.drop_table("process_part_instances")
    op.drop_table("process_recipes")
    op.drop_table("process_operations")
