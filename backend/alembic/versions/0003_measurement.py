"""Create measurement schema: data sources, connectors, imported files, runs,
samples, and the partitioned + immutable measurement_results table.

Revision ID: 0003_measurement
Revises: 0002_catalog
Create Date: 2026-07-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_measurement"
down_revision = "0002_catalog"
branch_labels = None
depends_on = None

# Monthly partitions pre-created for calendar year 2026 (the demo/pilot window).
# database/policies.md documents the maintenance job that must add future
# partitions ahead of time; a DEFAULT partition is the safety net meanwhile.
PARTITION_MONTHS = [f"{m:02d}" for m in range(1, 13)]


def upgrade() -> None:
    op.create_table(
        "measurement_data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("code", name="uq_measurement_data_sources_code"),
    )
    op.create_table(
        "measurement_connectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_source_id"], ["measurement_data_sources.id"], ondelete="RESTRICT",
            name="fk_measurement_connectors_data_source_id_measurement_da_d980",
        ),
        sa.UniqueConstraint(
            "data_source_id", "name", name="uq_measurement_connectors_data_source_id_name"
        ),
    )
    op.create_table(
        "measurement_imported_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("storage_bucket", sa.String(length=128), nullable=False),
        sa.Column("storage_object_key", sa.String(length=512), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("parse_status", sa.String(length=16), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_source_id"], ["measurement_data_sources.id"], ondelete="RESTRICT",
            name="fk_measurement_imported_files_data_source_id_measuremen_6a03",
        ),
        sa.ForeignKeyConstraint(
            ["connector_id"], ["measurement_connectors.id"], ondelete="RESTRICT",
            name="fk_measurement_imported_files_connector_id_measurement__ee2e",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"], ["security_users.id"], ondelete="SET NULL",
            name="fk_measurement_imported_files_uploaded_by_user_id_secur_3f81",
        ),
        sa.UniqueConstraint("sha256", name="uq_measurement_imported_files_sha256"),
    )
    op.create_table(
        "measurement_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("measurement_program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("machine_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("imported_file_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operator_identifier", sa.String(length=255), nullable=True),
        sa.Column("batch_lot", sa.String(length=128), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["measurement_program_id"], ["catalog_measurement_programs.id"], ondelete="RESTRICT",
            name="fk_measurement_runs_measurement_program_id_catalog_meas_235c",
        ),
        sa.ForeignKeyConstraint(
            ["machine_id"], ["org_machines.id"], ondelete="RESTRICT",
            name="fk_measurement_runs_machine_id_org_machines",
        ),
        sa.ForeignKeyConstraint(
            ["imported_file_id"], ["measurement_imported_files.id"], ondelete="RESTRICT",
            name="fk_measurement_runs_imported_file_id_measurement_imported_files",
        ),
    )
    op.create_table(
        "measurement_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("measurement_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sample_sequence", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["measurement_run_id"], ["measurement_runs.id"], ondelete="RESTRICT",
            name="fk_measurement_samples_measurement_run_id_measurement_runs",
        ),
        sa.UniqueConstraint(
            "measurement_run_id", "sample_sequence",
            name="uq_measurement_samples_measurement_run_id_sample_sequence",
        ),
    )

    # measurement_results: declarative RANGE partitioning + FKs are not
    # expressible via op.create_table, so this is raw DDL kept in lockstep
    # with app/models/measurement.py's MeasurementResult table metadata.
    op.execute(
        """
        CREATE TABLE measurement_results (
            id UUID NOT NULL,
            measured_at TIMESTAMPTZ NOT NULL,
            measurement_sample_id UUID NOT NULL,
            characteristic_id UUID NOT NULL,
            specification_id UUID NOT NULL,
            value NUMERIC(18, 6) NOT NULL,
            deviation NUMERIC(18, 6),
            is_ok BOOLEAN,
            supersedes_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pk_measurement_results PRIMARY KEY (id, measured_at),
            CONSTRAINT fk_measurement_results_measurement_sample_id_measuremen_e44e
                FOREIGN KEY (measurement_sample_id) REFERENCES measurement_samples (id) ON DELETE RESTRICT,
            CONSTRAINT fk_measurement_results_characteristic_id_catalog_charac_a56e
                FOREIGN KEY (characteristic_id) REFERENCES catalog_characteristics (id) ON DELETE RESTRICT,
            CONSTRAINT fk_measurement_results_specification_id_catalog_specifications
                FOREIGN KEY (specification_id) REFERENCES catalog_specifications (id) ON DELETE RESTRICT
        ) PARTITION BY RANGE (measured_at)
        """
    )
    op.create_index(
        "ix_measurement_results_characteristic_id_measured_at",
        "measurement_results",
        ["characteristic_id", "measured_at"],
    )

    for month in PARTITION_MONTHS:
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

    # Immutability: corrections insert a new row (supersedes_id), never update/delete
    # (CLAUDE.md §6 and §16). A row-level trigger on the partitioned parent is cloned
    # to every partition (including future ones) since PostgreSQL 11.
    op.execute(
        """
        CREATE FUNCTION prevent_measurement_result_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'measurement_results is immutable; insert a new row with supersedes_id set instead';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_measurement_results_no_update_delete
        BEFORE UPDATE OR DELETE ON measurement_results
        FOR EACH ROW
        EXECUTE FUNCTION prevent_measurement_result_mutation();
        """
    )
    op.execute("REVOKE UPDATE, DELETE ON TABLE measurement_results FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_measurement_results_no_update_delete ON measurement_results")
    op.execute("DROP FUNCTION IF EXISTS prevent_measurement_result_mutation()")
    op.drop_index(
        "ix_measurement_results_characteristic_id_measured_at",
        table_name="measurement_results",
    )
    op.execute("DROP TABLE measurement_results")  # cascades to all partitions
    op.drop_table("measurement_samples")
    op.drop_table("measurement_runs")
    op.drop_table("measurement_imported_files")
    op.drop_table("measurement_connectors")
    op.drop_table("measurement_data_sources")
