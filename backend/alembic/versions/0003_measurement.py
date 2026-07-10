"""Create measurement schema: connectors, data sources, imported files, runs,
samples, and a monthly-partitioned, insert-only results table.

Revision ID: 0003_measurement
Revises: 0002_catalog
Create Date: 2026-07-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_measurement"
down_revision = "0002_catalog"
branch_labels = None
depends_on = None

# measurement_results is partitioned by measured_at from the start (CLAUDE.md §6:
# results are the highest-volume table). Partitions are pre-created for calendar
# year 2026 plus a DEFAULT catch-all; ops extends this ahead of time per
# database/policies.md rather than relying on a rollover trigger.
_PARTITION_MONTHS = [f"{month:02d}" for month in range(1, 13)]


def upgrade() -> None:
    op.create_table(
        "measurement_connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_type", sa.String(length=64), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_measurement_connectors_code"),
    )
    op.create_table(
        "measurement_data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["connector_id"],
            ["measurement_connectors.id"],
            ondelete="RESTRICT",
            name="fk_measurement_data_sources_connector_id_measurement_co_1a2b",
        ),
        sa.UniqueConstraint("code", name="uq_measurement_data_sources_code"),
    )
    op.create_table(
        "measurement_imported_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("parse_status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["measurement_data_sources.id"],
            ondelete="RESTRICT",
            name="fk_measurement_imported_files_data_source_id_measuremen_9c3d",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["security_users.id"],
            ondelete="SET NULL",
            name="fk_measurement_imported_files_uploaded_by_user_id_secur_4e5f",
        ),
        sa.CheckConstraint(
            "parse_status IN ('pending', 'parsing', 'parsed', 'quarantined', 'error')",
            name="ck_measurement_imported_files_parse_status",
        ),
        sa.UniqueConstraint("sha256", name="uq_measurement_imported_files_sha256"),
    )
    op.create_table(
        "measurement_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("part_number_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("measurement_program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("imported_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_code", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["part_number_id"],
            ["catalog_part_numbers.id"],
            ondelete="RESTRICT",
            name="fk_measurement_runs_part_number_id_catalog_part_numbers",
        ),
        sa.ForeignKeyConstraint(
            ["measurement_program_id"],
            ["catalog_measurement_programs.id"],
            ondelete="RESTRICT",
            name="fk_measurement_runs_measurement_program_id_catalog_mea_6a7b",
        ),
        sa.ForeignKeyConstraint(
            ["data_source_id"],
            ["measurement_data_sources.id"],
            ondelete="RESTRICT",
            name="fk_measurement_runs_data_source_id_measurement_data_so_8c9d",
        ),
        sa.ForeignKeyConstraint(
            ["imported_file_id"],
            ["measurement_imported_files.id"],
            ondelete="RESTRICT",
            name="fk_measurement_runs_imported_file_id_measurement_impor_0e1f",
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"],
            ["org_machines.id"],
            ondelete="SET NULL",
            name="fk_measurement_runs_machine_id_org_machines",
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_measurement_runs_completed_after_started",
        ),
    )
    op.create_table(
        "measurement_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("measurement_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_index", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["measurement_run_id"],
            ["measurement_runs.id"],
            ondelete="RESTRICT",
            name="fk_measurement_samples_measurement_run_id_measurement_r_2a3b",
        ),
        sa.UniqueConstraint(
            "measurement_run_id", "sample_index", name="uq_measurement_samples_measurement_run_id_sample_index"
        ),
    )

    # measurement_results: partitioned parent + explicit monthly partitions for
    # 2026 + a DEFAULT partition. Raw SQL because SQLAlchemy's op.create_table
    # cannot express PARTITION BY. The partition key (measured_at) must be part
    # of every unique constraint, hence the composite primary key.
    #
    # supersedes_id intentionally has no FK: a self-reference into a partitioned
    # table would require a composite (id, measured_at) foreign key, forcing
    # every corrected row's caller to already know its predecessor's partition.
    # Lineage integrity is enforced at the service layer instead (mirrors the
    # deferred decision_id FK on catalog_inspection_frequencies in 0002).
    op.execute(
        """
        CREATE TABLE measurement_results (
            id UUID NOT NULL,
            measurement_sample_id UUID NOT NULL,
            characteristic_id UUID NOT NULL,
            specification_id UUID NOT NULL,
            value NUMERIC(18, 6) NOT NULL,
            deviation NUMERIC(18, 6) NOT NULL,
            is_ok BOOLEAN NOT NULL,
            measured_at TIMESTAMPTZ NOT NULL,
            supersedes_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_measurement_results PRIMARY KEY (id, measured_at),
            CONSTRAINT fk_measurement_results_measurement_sample_id_measure_3c4d
                FOREIGN KEY (measurement_sample_id)
                REFERENCES measurement_samples (id) ON DELETE RESTRICT,
            CONSTRAINT fk_measurement_results_characteristic_id_catalog_ch_5e6f
                FOREIGN KEY (characteristic_id)
                REFERENCES catalog_characteristics (id) ON DELETE RESTRICT,
            CONSTRAINT fk_measurement_results_specification_id_catalog_sp_7a8b
                FOREIGN KEY (specification_id)
                REFERENCES catalog_specifications (id) ON DELETE RESTRICT
        ) PARTITION BY RANGE (measured_at)
        """
    )
    for month in _PARTITION_MONTHS:
        next_month = f"{int(month) + 1:02d}" if month != "12" else "01"
        next_year = "2026" if month != "12" else "2027"
        op.execute(
            f"""
            CREATE TABLE measurement_results_2026_{month}
            PARTITION OF measurement_results
            FOR VALUES FROM ('2026-{month}-01') TO ('{next_year}-{next_month}-01')
            """
        )
    op.execute(
        "CREATE TABLE measurement_results_default PARTITION OF measurement_results DEFAULT"
    )
    op.execute(
        "CREATE INDEX ix_measurement_results_characteristic_id_measured_at "
        "ON measurement_results (characteristic_id, measured_at)"
    )

    # Insert-only enforcement (CLAUDE.md §6 / §16): corrections insert a new row
    # with supersedes_id set, never mutate or remove history. A row-level
    # trigger on the partitioned parent applies to every partition, present and
    # future (PostgreSQL 11+), so this can't be bypassed by inserting into a
    # partition directly.
    op.execute(
        """
        CREATE FUNCTION prevent_measurement_results_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'measurement_results is insert-only; corrections insert a new row with supersedes_id set';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_measurement_results_no_update_delete
        BEFORE UPDATE OR DELETE ON measurement_results
        FOR EACH ROW
        EXECUTE FUNCTION prevent_measurement_results_mutation();
        """
    )
    op.execute("REVOKE UPDATE, DELETE ON TABLE measurement_results FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_measurement_results_no_update_delete ON measurement_results")
    op.execute("DROP FUNCTION IF EXISTS prevent_measurement_results_mutation()")
    op.execute("DROP TABLE IF EXISTS measurement_results")
    op.drop_table("measurement_samples")
    op.drop_table("measurement_runs")
    op.drop_table("measurement_imported_files")
    op.drop_table("measurement_data_sources")
    op.drop_table("measurement_connectors")
