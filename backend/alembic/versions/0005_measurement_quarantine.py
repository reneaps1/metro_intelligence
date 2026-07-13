"""Create measurement_quarantined_rows: per-row import failures, kept with a
reason so a metrologist can inspect why a row was skipped (CLAUDE.md §6 --
invalid rows are quarantined, never silently dropped, and never mutate
measurement_results directly).

Revision ID: 0005_measurement_quarantine
Revises: 0004_context_intelligence
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_measurement_quarantine"
down_revision = "0004_context_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "measurement_quarantined_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("imported_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["imported_file_id"],
            ["measurement_imported_files.id"],
            ondelete="RESTRICT",
            name="fk_measurement_quarantined_rows_imported_file_id_measur_1a2b",
        ),
    )
    op.create_index(
        "ix_measurement_quarantined_rows_imported_file_id",
        "measurement_quarantined_rows",
        ["imported_file_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_measurement_quarantined_rows_imported_file_id",
        table_name="measurement_quarantined_rows",
    )
    op.drop_table("measurement_quarantined_rows")
