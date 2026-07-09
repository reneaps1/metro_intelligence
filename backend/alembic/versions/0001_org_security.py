"""Create org and security base schema.

Revision ID: 0001_org_security
Revises:
Create Date: 2026-07-09
"""
from __future__ import annotations

import secrets
import time
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_org_security"
down_revision = None
branch_labels = None
depends_on = None


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


ROLES = {
    "viewer": "Read-only dashboards and reports.",
    "metrologist": "Imports measurement files and reviews measurement evidence.",
    "quality_engineer": "Reviews risks and accepts or rejects recommendations.",
    "admin": "Administers master data, users, roles, permissions, and configuration.",
    "auditor": "Read-only access to the traceability record, including audit logs.",
}

ROLE_PERMISSIONS = {
    "org.organization": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "org.site": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "org.area": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "org.line": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "org.cell": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "assets.machine": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "catalog.product_family": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "catalog.part_number": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "catalog.characteristic": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "catalog.characteristic_classification": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "catalog.specification": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "catalog.measurement_program": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "catalog.inspection_plan": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["quality_engineer", "admin"],
        "update": ["quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "catalog.inspection_frequency": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["quality_engineer", "admin"],
        "update": ["quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "measurement.measurement_run": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["metrologist", "admin"],
        "administer": ["admin"],
    },
    "measurement.measurement_sample": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["metrologist", "admin"],
        "administer": ["admin"],
    },
    "measurement.measurement_result": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["metrologist", "admin"],
        "administer": ["admin"],
    },
    "measurement.imported_file": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["metrologist", "admin"],
        "administer": ["admin"],
    },
    "measurement.data_source": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "measurement.connector": {
        "read": ["quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "context.process_event": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["metrologist", "quality_engineer", "admin"],
        "update": ["quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "context.shift": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "context.operator": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "intelligence.risk_assessment": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "administer": ["admin"],
    },
    "intelligence.recommendation": {
        "read": ["metrologist", "quality_engineer", "admin", "auditor"],
        "update": ["admin"],
        "decide": ["quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "intelligence.decision": {
        "read": ["quality_engineer", "admin", "auditor"],
        "create": ["quality_engineer", "admin"],
        "decide": ["quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "intelligence.action_taken": {
        "read": ["quality_engineer", "admin", "auditor"],
        "create": ["quality_engineer", "admin"],
        "update": ["quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "intelligence.alert": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "update": ["viewer", "metrologist", "quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "security.user": {
        "read": ["admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "security.role": {
        "read": ["admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "security.permission": {
        "read": ["admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "security.audit_log": {
        "read": ["admin", "auditor"],
        "administer": ["admin"],
    },
    "presentation.dashboard": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["admin"],
        "update": ["viewer", "metrologist", "quality_engineer", "admin"],
        "administer": ["admin"],
    },
    "presentation.report": {
        "read": ["viewer", "metrologist", "quality_engineer", "admin", "auditor"],
        "create": ["metrologist", "quality_engineer", "admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
    "system.configuration": {
        "read": ["admin", "auditor"],
        "create": ["admin"],
        "update": ["admin"],
        "administer": ["admin"],
    },
}


def upgrade() -> None:
    op.create_table(
        "org_organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_org_organizations_code"),
    )
    op.create_table(
        "org_sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["org_organizations.id"], ondelete="RESTRICT", name="fk_org_sites_organization_id_org_organizations"),
        sa.UniqueConstraint("organization_id", "code", name="uq_org_sites_organization_id_code"),
    )
    op.create_table(
        "org_areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["org_sites.id"], ondelete="RESTRICT", name="fk_org_areas_site_id_org_sites"),
        sa.UniqueConstraint("site_id", "code", name="uq_org_areas_site_id_code"),
    )
    op.create_table(
        "org_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("area_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["org_areas.id"], ondelete="RESTRICT", name="fk_org_lines_area_id_org_areas"),
        sa.UniqueConstraint("area_id", "code", name="uq_org_lines_area_id_code"),
    )
    op.create_table(
        "org_cells",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["line_id"], ["org_lines.id"], ondelete="RESTRICT", name="fk_org_cells_line_id_org_lines"),
        sa.UniqueConstraint("line_id", "code", name="uq_org_cells_line_id_code"),
    )
    op.create_table(
        "org_machines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cell_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("machine_type", sa.String(length=64), nullable=True),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cell_id"], ["org_cells.id"], ondelete="RESTRICT", name="fk_org_machines_cell_id_org_cells"),
        sa.UniqueConstraint("cell_id", "code", name="uq_org_machines_cell_id_code"),
    )

    op.create_table(
        "security_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("email", name="uq_security_users_email"),
    )
    op.create_table(
        "security_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_security_roles_name"),
    )
    op.create_table(
        "security_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token", name="uq_security_permissions_token"),
    )
    op.create_table(
        "security_user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["security_users.id"], ondelete="CASCADE", name="fk_security_user_roles_user_id_security_users"),
        sa.ForeignKeyConstraint(["role_id"], ["security_roles.id"], ondelete="CASCADE", name="fk_security_user_roles_role_id_security_roles"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_security_user_roles_user_id_role_id"),
    )
    op.create_table(
        "security_role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.ForeignKeyConstraint(["role_id"], ["security_roles.id"], ondelete="CASCADE", name="fk_security_role_permissions_role_id_security_roles"),
        sa.ForeignKeyConstraint(["permission_id"], ["security_permissions.id"], ondelete="CASCADE", name="fk_security_role_permissions_permission_id_security_permissions"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_security_role_permissions_role_id_permission_id"),
    )
    op.create_table(
        "security_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_identifier", sa.String(length=320), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["security_users.id"], ondelete="SET NULL", name="fk_security_audit_log_actor_user_id_security_users"),
    )
    op.create_index("ix_security_audit_log_entity", "security_audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_security_audit_log_created_at", "security_audit_log", ["created_at"])

    op.execute(
        """
        CREATE FUNCTION prevent_security_audit_log_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'security_audit_log is append-only';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_security_audit_log_no_update_delete
        BEFORE UPDATE OR DELETE ON security_audit_log
        FOR EACH ROW
        EXECUTE FUNCTION prevent_security_audit_log_mutation();
        """
    )
    op.execute("REVOKE UPDATE, DELETE ON TABLE security_audit_log FROM PUBLIC")

    _seed_rbac()


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_security_audit_log_no_update_delete ON security_audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_security_audit_log_mutation()")
    op.drop_index("ix_security_audit_log_created_at", table_name="security_audit_log")
    op.drop_index("ix_security_audit_log_entity", table_name="security_audit_log")
    op.drop_table("security_audit_log")
    op.drop_table("security_role_permissions")
    op.drop_table("security_user_roles")
    op.drop_table("security_permissions")
    op.drop_table("security_roles")
    op.drop_table("security_users")
    op.drop_table("org_machines")
    op.drop_table("org_cells")
    op.drop_table("org_lines")
    op.drop_table("org_areas")
    op.drop_table("org_sites")
    op.drop_table("org_organizations")


def _seed_rbac() -> None:
    roles_table = sa.table(
        "security_roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_system", sa.Boolean()),
    )
    permissions_table = sa.table(
        "security_permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("token", sa.String()),
        sa.column("description", sa.Text()),
    )
    role_permissions_table = sa.table(
        "security_role_permissions",
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )

    role_ids = {name: _uuid7() for name in ROLES}
    op.bulk_insert(
        roles_table,
        [
            {
                "id": role_id,
                "name": name,
                "description": description,
                "is_system": True,
            }
            for name, role_id in role_ids.items()
            for description in [ROLES[name]]
        ],
    )

    token_roles: dict[str, set[str]] = {}
    for resource, actions in ROLE_PERMISSIONS.items():
        for action, roles in actions.items():
            token = f"{resource}.{action}"
            token_roles.setdefault(token, set()).update(roles)

    permission_ids = {token: _uuid7() for token in sorted(token_roles)}
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": permission_id,
                "token": token,
                "description": f"Allows {token}",
            }
            for token, permission_id in permission_ids.items()
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {
                "role_id": role_ids[role],
                "permission_id": permission_ids[token],
            }
            for token in sorted(token_roles)
            for role in sorted(token_roles[token])
        ],
    )
