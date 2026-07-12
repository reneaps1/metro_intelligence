"""F4.4 (MI-24): request/response schemas for the catalog CRUD API.

Versioned resources (Specification, MeasurementProgram, InspectionFrequency)
only ever get a *create-new-version* schema — there is no "update" schema for
them, because updating means closing the active row and inserting a new one
(CLAUDE.md §6, migration 0002_catalog.py's `valid_to IS NULL` partial unique
index). Non-versioned master data (ProductFamily, PartNumber, Characteristic,
CharacteristicClassification, InspectionPlan) gets ordinary create/update
schemas instead.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


# --- ProductFamily --------------------------------------------------------


class ProductFamilyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProductFamilyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class ProductFamilyRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- PartNumber ------------------------------------------------------------


class PartNumberCreate(BaseModel):
    product_family_id: uuid.UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class PartNumberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class PartNumberRead(BaseModel):
    id: uuid.UUID
    product_family_id: uuid.UUID
    code: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- CharacteristicClassification ------------------------------------------


class CharacteristicClassificationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None


class CharacteristicClassificationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = None


class CharacteristicClassificationRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Specification (versioned) ---------------------------------------------


class SpecificationCreate(BaseModel):
    """Payload for creating a *new version* of a characteristic's spec.

    ``lower_tol``/``upper_tol`` are signed offsets from ``nominal`` (e.g.
    nominal=10, lower_tol=-0.05, upper_tol=0.05). Either one may be omitted to
    represent a unilateral tolerance, but not both.
    """

    nominal: Decimal
    lower_tol: Decimal | None = None
    upper_tol: Decimal | None = None
    unit: str = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def _check_tolerances(self) -> SpecificationCreate:
        if self.lower_tol is None and self.upper_tol is None:
            raise ValueError("At least one of lower_tol/upper_tol must be provided.")
        lower_limit = self.nominal + self.lower_tol if self.lower_tol is not None else None
        upper_limit = self.nominal + self.upper_tol if self.upper_tol is not None else None
        if lower_limit is not None and lower_limit >= self.nominal:
            raise ValueError("lower_tol must place the lower limit below nominal.")
        if upper_limit is not None and upper_limit <= self.nominal:
            raise ValueError("upper_tol must place the upper limit above nominal.")
        if lower_limit is not None and upper_limit is not None and lower_limit >= upper_limit:
            raise ValueError("Computed lower limit must be less than the upper limit.")
        return self


class SpecificationRead(BaseModel):
    id: uuid.UUID
    characteristic_id: uuid.UUID
    nominal: Decimal
    lower_tol: Decimal | None
    upper_tol: Decimal | None
    unit: str
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Characteristic ---------------------------------------------------------


class CharacteristicCreate(BaseModel):
    part_number_id: uuid.UUID
    balloon_number: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    characteristic_type: str = Field(min_length=1, max_length=64)
    unit: str = Field(min_length=1, max_length=32)
    classification_id: uuid.UUID
    specification: SpecificationCreate


class CharacteristicUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    characteristic_type: str | None = Field(default=None, min_length=1, max_length=64)
    classification_id: uuid.UUID | None = None


class CharacteristicRead(BaseModel):
    id: uuid.UUID
    part_number_id: uuid.UUID
    balloon_number: str
    name: str
    characteristic_type: str
    unit: str
    classification_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    active_specification: SpecificationRead | None = None

    model_config = {"from_attributes": True}


# --- MeasurementProgram (versioned) -----------------------------------------


class MeasurementProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    output_mapping: dict[str, Any]

    @field_validator("output_mapping")
    @classmethod
    def _non_empty_mapping(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("output_mapping must not be empty.")
        return value


class MeasurementProgramRead(BaseModel):
    id: uuid.UUID
    part_number_id: uuid.UUID
    name: str
    version: int
    output_mapping: dict[str, Any]
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- InspectionPlan ----------------------------------------------------------


class InspectionPlanCreate(BaseModel):
    part_number_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True


class InspectionPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class InspectionPlanRead(BaseModel):
    id: uuid.UUID
    part_number_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- InspectionFrequency (versioned) -----------------------------------------


class InspectionFrequencyCreate(BaseModel):
    characteristic_id: uuid.UUID
    frequency_type: str = Field(min_length=1, max_length=32)
    frequency_value: Decimal
    reason: str | None = None

    @field_validator("frequency_value")
    @classmethod
    def _positive_frequency(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("frequency_value must be greater than zero.")
        return value


class InspectionFrequencyRead(BaseModel):
    id: uuid.UUID
    inspection_plan_id: uuid.UUID
    characteristic_id: uuid.UUID
    frequency_type: str
    frequency_value: Decimal
    reason: str | None
    changed_by_user_id: uuid.UUID | None
    decision_id: uuid.UUID | None
    valid_from: datetime
    valid_to: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
