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


class Connector(Base):
    __tablename__ = "measurement_connectors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    data_sources: Mapped[list[DataSource]] = relationship(back_populates="connector")


class DataSource(Base):
    __tablename__ = "measurement_data_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    connector_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_connectors.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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

    connector: Mapped[Connector] = relationship(back_populates="data_sources")
    imported_files: Mapped[list[ImportedFile]] = relationship(back_populates="data_source")
    runs: Mapped[list[MeasurementRun]] = relationship(back_populates="data_source")


class ImportedFile(Base):
    __tablename__ = "measurement_imported_files"
    __table_args__ = (
        CheckConstraint(
            "parse_status IN ('pending', 'parsing', 'parsed', 'quarantined', 'error')",
            name="ck_measurement_imported_files_parse_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_data_sources.id", ondelete="RESTRICT"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    data_source: Mapped[DataSource] = relationship(back_populates="imported_files")
    runs: Mapped[list[MeasurementRun]] = relationship(back_populates="imported_file")


class MeasurementRun(Base):
    __tablename__ = "measurement_runs"
    __table_args__ = (
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at",
            name="ck_measurement_runs_completed_after_started",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    part_number_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"), nullable=False
    )
    measurement_program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_measurement_programs.id", ondelete="RESTRICT"), nullable=False
    )
    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_data_sources.id", ondelete="RESTRICT"), nullable=False
    )
    imported_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("measurement_imported_files.id", ondelete="RESTRICT"), nullable=True
    )
    machine_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_machines.id", ondelete="SET NULL"), nullable=True
    )
    batch_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    data_source: Mapped[DataSource] = relationship(back_populates="runs")
    imported_file: Mapped[ImportedFile | None] = relationship(back_populates="runs")
    samples: Mapped[list[MeasurementSample]] = relationship(back_populates="measurement_run")


class MeasurementSample(Base):
    __tablename__ = "measurement_samples"
    __table_args__ = (
        UniqueConstraint(
            "measurement_run_id",
            "sample_index",
            name="uq_measurement_samples_measurement_run_id_sample_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    measurement_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_runs.id", ondelete="RESTRICT"), nullable=False
    )
    sample_index: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    measurement_run: Mapped[MeasurementRun] = relationship(back_populates="samples")
    results: Mapped[list[MeasurementResult]] = relationship(back_populates="measurement_sample")


class MeasurementResult(Base):
    """Insert-only, monthly-partitioned by `measured_at` (migration 0003).
    Corrections insert a new row with `supersedes_id` set; UPDATE/DELETE are
    blocked by a DB trigger regardless of caller privileges (CLAUDE.md §6, §16).
    `supersedes_id` has no FK — see the migration for why."""

    __tablename__ = "measurement_results"
    __table_args__ = (
        Index(
            "ix_measurement_results_characteristic_id_measured_at",
            "characteristic_id",
            "measured_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
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
    deviation: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    is_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    measurement_sample: Mapped[MeasurementSample] = relationship(back_populates="results")
