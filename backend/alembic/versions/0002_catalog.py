"""Create catalog schema: product families, parts, characteristics, versioned
specifications, measurement programs, inspection plans and frequency history.

Revision ID: 0002_catalog
Revises: 0001_org_security
Create Date: 2026-07-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_catalog"
down_revision = "0001_org_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catalog_product_families",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_catalog_product_families_code"),
    )
    op.create_table(
        "catalog_part_numbers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("product_family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_family_id"],
            ["catalog_product_families.id"],
            ondelete="RESTRICT",
            name="fk_catalog_part_numbers_product_family_id_catalog_produ_e905",
        ),
        sa.UniqueConstraint("code", name="uq_catalog_part_numbers_code"),
    )
    op.create_table(
        "catalog_characteristic_classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_catalog_characteristic_classifications_code"),
    )
    op.create_table(
        "catalog_characteristics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("part_number_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("balloon_number", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("characteristic_type", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("classification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["part_number_id"],
            ["catalog_part_numbers.id"],
            ondelete="RESTRICT",
            name="fk_catalog_characteristics_part_number_id_catalog_part_numbers",
        ),
        sa.ForeignKeyConstraint(
            ["classification_id"],
            ["catalog_characteristic_classifications.id"],
            ondelete="RESTRICT",
            name="fk_catalog_characteristics_classification_id_catalog_ch_096f",
        ),
        sa.UniqueConstraint(
            "part_number_id",
            "balloon_number",
            name="uq_catalog_characteristics_part_number_id_balloon_number",
        ),
    )
    op.create_table(
        "catalog_specifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("characteristic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nominal", sa.Numeric(18, 6), nullable=False),
        sa.Column("lower_tol", sa.Numeric(18, 6), nullable=True),
        sa.Column("upper_tol", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["characteristic_id"],
            ["catalog_characteristics.id"],
            ondelete="RESTRICT",
            name="fk_catalog_specifications_characteristic_id_catalog_cha_5374",
        ),
        sa.CheckConstraint(
            "lower_tol IS NOT NULL OR upper_tol IS NOT NULL",
            name="ck_catalog_specifications_tolerance_present",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_catalog_specifications_valid_range",
        ),
    )
    op.create_index(
        "uq_catalog_specifications_active_characteristic",
        "catalog_specifications",
        ["characteristic_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
    )
    op.create_table(
        "catalog_measurement_programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("part_number_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("output_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["part_number_id"],
            ["catalog_part_numbers.id"],
            ondelete="RESTRICT",
            name="fk_catalog_measurement_programs_part_number_id_catalog__60bc",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_catalog_measurement_programs_valid_range",
        ),
    )
    op.create_index(
        "uq_catalog_measurement_programs_active_program",
        "catalog_measurement_programs",
        ["part_number_id", "name"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
    )
    op.create_table(
        "catalog_inspection_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("part_number_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["part_number_id"],
            ["catalog_part_numbers.id"],
            ondelete="RESTRICT",
            name="fk_catalog_inspection_plans_part_number_id_catalog_part_numbers",
        ),
        sa.UniqueConstraint(
            "part_number_id", "name", name="uq_catalog_inspection_plans_part_number_id_name"
        ),
    )
    op.create_table(
        "catalog_inspection_frequencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("inspection_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("characteristic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frequency_type", sa.String(length=32), nullable=False),
        sa.Column("frequency_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["inspection_plan_id"],
            ["catalog_inspection_plans.id"],
            ondelete="RESTRICT",
            name="fk_catalog_inspection_frequencies_inspection_plan_id_ca_1c36",
        ),
        sa.ForeignKeyConstraint(
            ["characteristic_id"],
            ["catalog_characteristics.id"],
            ondelete="RESTRICT",
            name="fk_catalog_inspection_frequencies_characteristic_id_cat_9f35",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["security_users.id"],
            ondelete="SET NULL",
            name="fk_catalog_inspection_frequencies_changed_by_user_id_se_5cb2",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_catalog_inspection_frequencies_valid_range",
        ),
    )
    op.create_index(
        "uq_catalog_inspection_frequencies_active",
        "catalog_inspection_frequencies",
        ["inspection_plan_id", "characteristic_id"],
        unique=True,
        postgresql_where=sa.text("valid_to IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_catalog_inspection_frequencies_active", table_name="catalog_inspection_frequencies")
    op.drop_table("catalog_inspection_frequencies")
    op.drop_table("catalog_inspection_plans")
    op.drop_index("uq_catalog_measurement_programs_active_program", table_name="catalog_measurement_programs")
    op.drop_table("catalog_measurement_programs")
    op.drop_index("uq_catalog_specifications_active_characteristic", table_name="catalog_specifications")
    op.drop_table("catalog_specifications")
    op.drop_table("catalog_characteristics")
    op.drop_table("catalog_characteristic_classifications")
    op.drop_table("catalog_part_numbers")
    op.drop_table("catalog_product_families")
