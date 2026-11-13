"""Daily statistics: count gross readings apart from the moments (ADR-005).

`process_characteristic_daily.n_gross` holds the values so far outside the
tolerance that they are measurement failures, not process spread. They stay
in `n`, the NOK counts, `min_value` and `max_value`, and leave only
`sum_value` / `sum_sq_value`, so the mean, the standard deviation and the
capability describe the process. Existing rows read 0 until the next
`build_daily_stats`.

Revision ID: 0010_gross_readings
Revises: 0009_process_model
Create Date: 2026-11-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_gross_readings"
down_revision = "0009_process_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "process_characteristic_daily",
        sa.Column("n_gross", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("process_characteristic_daily", "n_gross")
