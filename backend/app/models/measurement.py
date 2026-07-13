from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid7
from app.models.catalog import MeasurementProgram


class DataSource(Base):
    """Registry of where measurement data comes from (CLAUDE.md §3: decoupled connector layer)."""

    __tablename__ = "measurement_data_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    connectors: Mapped[list[Connector]] = relationship(back_populates="data_source")
    imported_files: Mapped[list[ImportedFile]] = relationship(back_populates="data_source")


class Connector(Base):
    __tablename__ = "measurement_connectors"
    __table_args__ = (
        UniqueConstraint("data_source_id", "name", name="uq_measurement_connectors_data_source_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_data_sources.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    data_source: Mapped[DataSource] = relationship(back_populates="connectors")
    imported_files: Mapped[list[ImportedFile]] = relationship(back_populates="connector")


class ImportedFile(Base):
    """Original artifact retained in MinIO; sha256 drives dedup (CLAUDE.md §6)."""

    __tablename__ = "measurement_imported_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_data_sources.id", ondelete="RESTRICT"), nullable=False
    )
    connector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("measurement_connectors.id", ondelete="RESTRICT"), nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parse_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    data_source: Mapped[DataSource] = relationship(back_populates="imported_files")
    connector: Mapped[Connector | None] = relationship(back_populates="imported_files")
    runs: Mapped[list[MeasurementRun]] = relationship(back_populates="imported_file")
    quarantined_rows: Mapped[list[QuarantinedRow]] = relationship(back_populates="imported_file")


class QuarantinedRow(Base):
    """One rejected row from an import: kept with its raw data and the reason
    it was rejected so a metrologist can inspect and fix the source file,
    rather than the row being silently dropped (CLAUDE.md §6)."""

    __tablename__ = "measurement_quarantined_rows"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    imported_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_imported_files.id", ondelete="RESTRICT"), nullable=False
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_row: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    imported_file: Mapped[ImportedFile] = relationship(back_populates="quarantined_rows")


class MeasurementRun(Base):
    """One execution of a measurement program (a "report")."""

    __tablename__ = "measurement_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    measurement_program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_measurement_programs.id", ondelete="RESTRICT"), nullable=False
    )
    machine_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_machines.id", ondelete="RESTRICT"), nullable=True
    )
    imported_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("measurement_imported_files.id", ondelete="RESTRICT"), nullable=True
    )
    operator_identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_lot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    imported_file: Mapped[ImportedFile | None] = relationship(back_populates="runs")
    samples: Mapped[list[MeasurementSample]] = relationship(back_populates="measurement_run")
    measurement_program: Mapped[MeasurementProgram] = relationship()


class MeasurementSample(Base):
    """One physical part measured within a run."""

    __tablename__ = "measurement_samples"
    __table_args__ = (
        UniqueConstraint(
            "measurement_run_id",
            "sample_sequence",
            name="uq_measurement_samples_measurement_run_id_sample_sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    measurement_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_runs.id", ondelete="RESTRICT"), nullable=False
    )
    sample_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    measurement_run: Mapped[MeasurementRun] = relationship(back_populates="samples")
    results: Mapped[list[MeasurementResult]] = relationship(back_populates="measurement_sample")


class MeasurementResult(Base):
    """One measured value for one characteristic of one sample.

    Immutable once inserted (enforced by a DB trigger, not just app convention —
    see migration 0003): corrections insert a new row with `supersedes_id` set.
    Partitioned by range on `measured_at`; `supersedes_id` is intentionally a bare
    column (no FK) since Postgres native partitioning cannot enforce a normal FK
    into a partitioned table without also carrying the partition key.
    """

    __tablename__ = "measurement_results"
    __table_args__ = (
        Index("ix_measurement_results_characteristic_id_measured_at", "characteristic_id", "measured_at"),
        {"postgresql_partition_by": "RANGE (measured_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    measurement_sample_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_samples.id", ondelete="RESTRICT"), nullable=False
    )
    characteristic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristics.id", ondelete="RESTRICT"), nullable=False
    )
    specification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_specifications.id", ondelete="RESTRICT"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    deviation: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    is_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    measurement_sample: Mapped[MeasurementSample] = relationship(back_populates="results")
