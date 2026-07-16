"""LM.1: add the `live_monitor.stream` permission token (action `read`),
granted to the same roles as `context.process_event.read` (metrologist,
quality_engineer, admin, auditor -- CLAUDE.md §5, docs/tasks/LM1-live-monitor-mvp.md).

Revision ID: 0006_live_monitor_permission
Revises: 0005_measurement_quarantine
Create Date: 2026-07-15
"""
from __future__ import annotations

import secrets
import time
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_live_monitor_permission"
down_revision = "0005_measurement_quarantine"
branch_labels = None
depends_on = None

TOKEN = "live_monitor.stream"
GRANTED_ROLES = ["metrologist", "quality_engineer", "admin", "auditor"]


def _uuid7() -> uuid.UUID:
    unix_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (
        (unix_ms << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0b10 << 62)
        | rand_b
    )
    return uuid.UUID(int=value)


def upgrade() -> None:
    conn = op.get_bind()

    permission_id = _uuid7()
    op.bulk_insert(
        sa.table(
            "security_permissions",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("token", sa.String()),
            sa.column("description", sa.Text()),
        ),
        [{"id": permission_id, "token": TOKEN, "description": f"Allows {TOKEN}"}],
    )

    role_ids = conn.execute(
        sa.text("SELECT id, name FROM security_roles WHERE name = ANY(:names)"),
        {"names": GRANTED_ROLES},
    ).all()

    op.bulk_insert(
        sa.table(
            "security_role_permissions",
            sa.column("role_id", postgresql.UUID(as_uuid=True)),
            sa.column("permission_id", postgresql.UUID(as_uuid=True)),
        ),
        [{"role_id": role_id, "permission_id": permission_id} for role_id, _name in role_ids],
    )


def downgrade() -> None:
    conn = op.get_bind()
    permission_id = conn.execute(
        sa.text("SELECT id FROM security_permissions WHERE token = :token"), {"token": TOKEN}
    ).scalar_one_or_none()
    if permission_id is not None:
        conn.execute(
            sa.text("DELETE FROM security_role_permissions WHERE permission_id = :pid"),
            {"pid": permission_id},
        )
        conn.execute(
            sa.text("DELETE FROM security_permissions WHERE id = :pid"), {"pid": permission_id}
        )
