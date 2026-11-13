"""IQ-F6: request/response models for the exploratory dimensional CSV import."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.quality_analytics import DatasetOut

ColumnName = Field(default=None, max_length=64)


class ColumnProfileOut(BaseModel):
    name: str
    kind: Literal["number", "integer", "datetime", "text", "empty"]
    non_empty: int
    examples: list[str]


class SuggestedMappingOut(BaseModel):
    layout: Literal["long", "wide"]
    roles: dict[str, str]
    value_columns: list[str]


class ImportLimits(BaseModel):
    max_bytes: int
    max_rows: int


class PreviewResponse(BaseModel):
    encoding: str
    delimiter: str
    decimal: Literal[".", ","]
    date_order: Literal["ymd", "dmy", "mdy"]
    header: list[str]
    rows: list[list[str]]
    profiles: list[ColumnProfileOut]
    suggestion: SuggestedMappingOut
    sampled_rows: int
    limits: ImportLimits


class VariableSpecIn(BaseModel):
    nominal: float | None = None
    lsl: float | None = None
    usl: float | None = None
    unit: str | None = Field(default=None, max_length=16)


class ColumnMappingIn(BaseModel):
    layout: Literal["long", "wide"]
    delimiter: Literal[",", ";", "\t", "|"]
    decimal: Literal[".", ","]
    date_order: Literal["ymd", "dmy", "mdy"] = "dmy"
    timestamp: str = Field(min_length=1, max_length=64)
    time: str | None = ColumnName
    piece_id: str | None = ColumnName
    group: str | None = ColumnName
    cavity: str | None = ColumnName
    machine: str | None = ColumnName
    shift: str | None = ColumnName
    batch: str | None = ColumnName
    ok_nok: str | None = ColumnName
    variable: str | None = ColumnName
    value: str | None = ColumnName
    nominal: str | None = ColumnName
    lsl: str | None = ColumnName
    usl: str | None = ColumnName
    unit: str | None = ColumnName
    value_columns: list[str] = Field(default_factory=list, max_length=200)
    specs: dict[str, VariableSpecIn] = Field(default_factory=dict, max_length=200)
    name: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def _limits_ordered(self) -> ColumnMappingIn:
        for key, spec in self.specs.items():
            if spec.lsl is not None and spec.usl is not None and spec.lsl > spec.usl:
                raise ValueError(f"LIE > LSE para «{key}».")
        return self


class QuarantineReason(BaseModel):
    reason: str
    rows: int


class QuarantineExample(BaseModel):
    row_number: int
    reason: str


class SampleNotice(BaseModel):
    limited: bool
    rows_read: int
    approx_file_pct: float | None
    file_bytes: int
    bytes_analysed: int


class ImportReport(BaseModel):
    filename: str
    layout: Literal["long", "wide"]
    rows_read: int
    rows_accepted: int
    rows_quarantined: int
    pieces: int
    variables: int
    empty_values: int
    quarantine_by_reason: list[QuarantineReason]
    quarantine_examples: list[QuarantineExample]
    warnings: list[str]
    sample: SampleNotice


class ImportedDatasetResponse(BaseModel):
    report: ImportReport
    # None when no row survived validation (the report says why).
    dataset: DatasetOut | None
