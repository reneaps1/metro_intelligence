from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
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


class ProductFamily(Base):
    __tablename__ = "catalog_product_families"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
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

    part_numbers: Mapped[list[PartNumber]] = relationship(back_populates="product_family")


class PartNumber(Base):
    __tablename__ = "catalog_part_numbers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    product_family_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_product_families.id", ondelete="RESTRICT"), nullable=False
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

    product_family: Mapped[ProductFamily] = relationship(back_populates="part_numbers")
    characteristics: Mapped[list[Characteristic]] = relationship(back_populates="part_number")
    measurement_programs: Mapped[list[MeasurementProgram]] = relationship(
        back_populates="part_number"
    )
    inspection_plans: Mapped[list[InspectionPlan]] = relationship(back_populates="part_number")


class CharacteristicClassification(Base):
    __tablename__ = "catalog_characteristic_classifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    characteristics: Mapped[list[Characteristic]] = relationship(back_populates="classification")


class Characteristic(Base):
    __tablename__ = "catalog_characteristics"
    __table_args__ = (
        UniqueConstraint(
            "part_number_id",
            "balloon_number",
            name="uq_catalog_characteristics_part_number_id_balloon_number",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    part_number_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"), nullable=False
    )
    balloon_number: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    characteristic_type: Mapped[str] = mapped_column(String(64), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    classification_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristic_classifications.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    part_number: Mapped[PartNumber] = relationship(back_populates="characteristics")
    classification: Mapped[CharacteristicClassification] = relationship(
        back_populates="characteristics"
    )
    specifications: Mapped[list[Specification]] = relationship(back_populates="characteristic")
    inspection_frequencies: Mapped[list[InspectionFrequency]] = relationship(
        back_populates="characteristic"
    )


class Specification(Base):
    """Versioned nominal + tolerance record. Exactly one active row (valid_to IS NULL)
    per characteristic; results reference the version in force when measured and are
    never re-evaluated against a later version (CLAUDE.md §6)."""

    __tablename__ = "catalog_specifications"
    __table_args__ = (
        CheckConstraint(
            "lower_tol IS NOT NULL OR upper_tol IS NOT NULL",
            name="ck_catalog_specifications_tolerance_present",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_catalog_specifications_valid_range",
        ),
        Index(
            "uq_catalog_specifications_active_characteristic",
            "characteristic_id",
            unique=True,
            postgresql_where="valid_to IS NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    characteristic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristics.id", ondelete="RESTRICT"), nullable=False
    )
    nominal: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    lower_tol: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    upper_tol: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    characteristic: Mapped[Characteristic] = relationship(back_populates="specifications")


class MeasurementProgram(Base):
    """Named program (e.g. a PolyWorks routine) mapping outputs to characteristics.
    Versioned like Specification: exactly one active version per (part_number, name)."""

    __tablename__ = "catalog_measurement_programs"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_catalog_measurement_programs_valid_range",
        ),
        Index(
            "uq_catalog_measurement_programs_active_program",
            "part_number_id",
            "name",
            unique=True,
            postgresql_where="valid_to IS NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    part_number_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    output_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    part_number: Mapped[PartNumber] = relationship(back_populates="measurement_programs")


class InspectionPlan(Base):
    __tablename__ = "catalog_inspection_plans"
    __table_args__ = (
        UniqueConstraint(
            "part_number_id", "name", name="uq_catalog_inspection_plans_part_number_id_name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    part_number_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_part_numbers.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    part_number: Mapped[PartNumber] = relationship(back_populates="inspection_plans")
    frequencies: Mapped[list[InspectionFrequency]] = relationship(
        back_populates="inspection_plan"
    )


class InspectionFrequency(Base):
    """History row for a sampling frequency on one characteristic within a plan.
    `decision_id` is a bare column (no FK yet): the `intelligence.decision` table is
    created in migration 0004 (F2.4), which will add the constraint."""

    __tablename__ = "catalog_inspection_frequencies"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_catalog_inspection_frequencies_valid_range",
        ),
        Index(
            "uq_catalog_inspection_frequencies_active",
            "inspection_plan_id",
            "characteristic_id",
            unique=True,
            postgresql_where="valid_to IS NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)
    inspection_plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_inspection_plans.id", ondelete="RESTRICT"), nullable=False
    )
    characteristic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_characteristics.id", ondelete="RESTRICT"), nullable=False
    )
    frequency_type: Mapped[str] = mapped_column(String(32), nullable=False)
    frequency_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("security_users.id", ondelete="SET NULL"), nullable=True
    )
    decision_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    inspection_plan: Mapped[InspectionPlan] = relationship(back_populates="frequencies")
    characteristic: Mapped[Characteristic] = relationship(back_populates="inspection_frequencies")
