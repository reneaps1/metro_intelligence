"""Process model: line steps, recipes, physical pieces and per-step results
(ADR-005).

Measurement values stay in `measurement_results`; these tables add the
process structure around them. The `*_daily` tables are derived statistics
rebuilt by `app.cli.build_daily_stats`, not measurement history.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid7

OPERATION_KINDS = ("electrical", "pin_length", "pin_position", "type_check")
OPERATION_SIDES = ("pcb", "connector")


class Operation(Base):
    """One step of a line, in `sequence` order."""

    __tablename__ = "process_operations"
    __table_args__ = (
        UniqueConstraint("line_id", "sequence", name="uq_process_operations_line_id_sequence"),
        UniqueConstraint("line_id", "code", name="uq_process_operations_line_id_code"),
        CheckConstraint(
            "operation_kind IN ('electrical', 'pin_length', 'pin_position', 'type_check')",
            name="operation_kind",
        ),
        CheckConstraint("side IS NULL OR side IN ('pcb', 'connector')", name="side"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_lines.id", ondelete="RESTRICT"), nullable=False
    )
    machine_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_machines.id", ondelete="RESTRICT"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Recipe(Base):
    """Station program that identifies the product variant. The variant
    fields are set later by `relabel_recipe` without reloading data."""

    __tablename__ = "process_recipes"
    __table_args__ = (UniqueConstraint("line_id", "code", name="uq_process_recipes_line_id_code"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_lines.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    part_number_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"), nullable=False
    )
    variant_part_number_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"), nullable=True
    )
    variant_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PartInstance(Base):
    """One physical piece on a line, identified by the stations' piece id."""

    __tablename__ = "process_part_instances"
    __table_args__ = (
        UniqueConstraint("line_id", "serial_number", name="uq_process_part_instances_line_id_serial_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("org_lines.id", ondelete="RESTRICT"), nullable=False
    )
    serial_number: Mapped[str] = mapped_column(String(64), nullable=False)
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("process_recipes.id", ondelete="RESTRICT"), nullable=True
    )
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StepResult(Base):
    """One station row for one piece. Insert-only: a repeated row for the
    same piece and step is a new row with a higher `attempt_no`."""

    __tablename__ = "process_step_results"
    __table_args__ = (
        Index("ix_process_step_results_operation_id_recorded_at", "operation_id", "recorded_at"),
        Index("ix_process_step_results_part_instance_id", "part_instance_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    part_instance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("process_part_instances.id", ondelete="RESTRICT"), nullable=False
    )
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("process_operations.id", ondelete="RESTRICT"), nullable=False
    )
    measurement_sample_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("measurement_samples.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    nest: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    program_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    machine_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    error_count: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reference_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    attempt_no: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)


class StepDaily(Base):
    """Derived: pieces per day, step, recipe and nest."""

    __tablename__ = "process_step_daily"
    __table_args__ = (Index("ix_process_step_daily_operation_id_day", "operation_id", "day"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("process_operations.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("process_recipes.id", ondelete="CASCADE"), nullable=True
    )
    nest: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    pieces: Mapped[int] = mapped_column(Integer, nullable=False)
    pieces_machine_nok: Mapped[int] = mapped_column(Integer, nullable=False)
    pieces_spec_nok: Mapped[int] = mapped_column(Integer, nullable=False)
    first_attempt_ok: Mapped[int] = mapped_column(Integer, nullable=False)
    repeat_attempts: Mapped[int] = mapped_column(Integer, nullable=False)


class CharacteristicDaily(Base):
    """Derived: value moments and verdict counts per day, step, recipe,
    nest, characteristic and specification version."""

    __tablename__ = "process_characteristic_daily"
    __table_args__ = (
        Index("ix_process_characteristic_daily_operation_id_day", "operation_id", "day"),
        Index("ix_process_characteristic_daily_characteristic_id_day", "characteristic_id", "day"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    operation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("process_operations.id", ondelete="CASCADE"), nullable=False
    )
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("process_recipes.id", ondelete="CASCADE"), nullable=True
    )
    nest: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    characteristic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristics.id", ondelete="CASCADE"), nullable=False
    )
    specification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_specifications.id", ondelete="CASCADE"), nullable=True
    )
    n: Mapped[int] = mapped_column(Integer, nullable=False)
    n_machine_nok: Mapped[int] = mapped_column(Integer, nullable=False)
    n_evaluated: Mapped[int] = mapped_column(Integer, nullable=False)
    n_spec_nok: Mapped[int] = mapped_column(Integer, nullable=False)
    n_machine_ok_spec_nok: Mapped[int] = mapped_column(Integer, nullable=False)
    sum_value: Mapped[float] = mapped_column(Double, nullable=False)
    sum_sq_value: Mapped[float] = mapped_column(Double, nullable=False)
    min_value: Mapped[float] = mapped_column(Double, nullable=False)
    max_value: Mapped[float] = mapped_column(Double, nullable=False)


class StatsBuild(Base):
    """Traceability of each rebuild of the daily tables."""

    __tablename__ = "process_stats_builds"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    built_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("org_lines.id", ondelete="CASCADE"), nullable=False)
    engine_name: Mapped[str] = mapped_column(String(64), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(postgresql.JSONB, nullable=False)
