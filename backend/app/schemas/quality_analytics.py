"""IQ-F5: response models for the dimensional quality analytics API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["SIMULATED", "REAL", "IMPORTED"]


class VariableOut(BaseModel):
    key: str
    name: str
    unit: str
    # None when the source only gave limits (no nominal to show).
    nominal: float | None
    lsl: float | None
    usl: float | None


class AvailableFilters(BaseModel):
    machine: bool
    cavity: bool
    shift: bool
    batch: bool
    # IQ-F10: mold cavity (second grouping), station verdicts, data-quality flags.
    mold_cavity: bool = False
    station: bool = False
    quality_flags: bool = False


class StationOut(BaseModel):
    key: str
    name: str


class PresetOut(BaseModel):
    key: str
    label: str
    stations: list[str]
    group_by: Literal["nest", "mold_cavity"]


class DatasetOut(BaseModel):
    id: str
    name: str
    description: str
    source_type: SourceType
    period_start: datetime
    period_end: datetime
    pieces: int
    groups: int
    variables: list[VariableOut]
    machines: list[str]
    cavities: list[int]
    shifts: list[str]
    batches: list[str]
    available_filters: AvailableFilters
    mechanisms: list[str]
    # IQ-F6: the source file carries its own OK/NOK verdict column.
    has_reported_verdict: bool = False
    # --- IQ-F10 (REAL datasets) ---
    mold_cavities: list[int] = Field(default_factory=list)
    stations: list[StationOut] = Field(default_factory=list)
    nok_basis: Literal["spec", "reported"] = "spec"
    # Plant local time = UTC + offset; buckets of this dataset use it.
    utc_offset_minutes: int = 0
    has_groups: bool = True
    presets: list[PresetOut] = Field(default_factory=list)
    # Counts only, from the offline conversion report (no identifiers).
    data_quality: dict[str, int] = Field(default_factory=dict)


class DatasetListResponse(BaseModel):
    items: list[DatasetOut]


class CavityRate(BaseModel):
    cavity: int
    pieces: int
    nok: int
    rate: float | None
    ci_low: float | None
    ci_high: float | None
    relative_risk: float | None


class SourceReported(BaseModel):
    """Piece verdict carried by the imported file vs. the one recalculated from spec."""

    pieces_with_verdict: int
    nok_pieces: int
    nok_rate: float | None
    both_nok: int
    source_only_nok: int
    spec_only_nok: int
    both_ok: int
    definition: str


class Summary(BaseModel):
    groups: int
    pieces: int
    measurements: int
    ok_pieces: int
    nok_pieces: int
    nok_rate: float | None
    nok_rate_ci: tuple[float, float] | None
    measurement_nok: int
    top_variables: list[str]
    worst_cavity: CavityRate | None
    period_start: datetime | None
    period_end: datetime | None
    nok_definition: str
    variables_counted: list[str]
    variables_with_tolerance: int
    source_reported: SourceReported | None = None
    nok_basis: Literal["spec", "reported"] = "spec"
    stations_counted: list[str] = Field(default_factory=list)
    pieces_without_verdict: int = 0
    worst_mold_cavity: CavityRate | None = None


class StationParetoRow(BaseModel):
    """NOK pieces attributed to their first failing station (process order)."""

    station: str
    name: str
    nok: int
    fails_any: int
    share: float | None
    cumulative_pct: float | None


class TrendBucket(BaseModel):
    bucket: str
    start: datetime | None
    pieces: int
    nok: int
    rate: float | None


class ParetoRow(BaseModel):
    variable: str
    name: str
    nok: int
    above: int
    below: int
    measurements: int
    cumulative_pct: float | None


class HeatmapCell(BaseModel):
    cavity: int
    variable: str
    pieces: int
    nok: int
    rate: float | None


class OverviewResponse(BaseModel):
    dataset_id: str
    source_type: SourceType
    granularity: Literal["day", "hour", "shift"]
    summary: Summary
    trend: list[TrendBucket]
    pareto: list[ParetoRow]
    by_cavity: list[CavityRate]
    heatmap: list[HeatmapCell]
    by_mold_cavity: list[CavityRate] = Field(default_factory=list)
    station_pareto: list[StationParetoRow] = Field(default_factory=list)
    # "variable": cells are nest x variable; "station": nest x first failing station.
    heatmap_axis: Literal["variable", "station"] = "variable"


class Spec(BaseModel):
    nominal: float | None
    lsl: float | None
    usl: float | None
    unit: str


class Capability(BaseModel):
    cp: float | None
    cpk: float | None
    reason: str | None


class ControlLimitsOut(BaseModel):
    center_line: float
    ucl: float
    lcl: float
    engine: str


class HistogramBin(BaseModel):
    x0: float
    x1: float
    count: int


class GroupBox(BaseModel):
    group: str
    n: int
    min: float
    q1: float
    median: float
    q3: float
    max: float
    whisker_low: float
    whisker_high: float
    outliers: int
    mean: float
    nok: int
    nok_rate: float


class DailyCpk(BaseModel):
    day: str
    n: int
    cpk: float | None


class VariableDetailResponse(BaseModel):
    dataset_id: str
    source_type: SourceType
    variable: str
    name: str
    spec: Spec
    n: int
    nok: int = 0
    nok_rate: float | None = None
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    capability: Capability | None = None
    control_limits: ControlLimitsOut | None = None
    histogram: list[HistogramBin] = Field(default_factory=list)
    # [epoch ms, value, is_nok]
    series: list[tuple[int, float, bool]] = Field(default_factory=list)
    series_thinned: bool = False
    group_by: Literal["cavity", "machine", "shift", "batch", "mold_cavity"] = "cavity"
    groups: list[GroupBox] = Field(default_factory=list)
    cpk_by_day: list[DailyCpk] = Field(default_factory=list)
    nok_basis: Literal["spec", "reported"] = "spec"
    # What the NOK markers mean ("fuera de tolerancia" / "rechazadas por la estación ...").
    nok_label: str = "fuera de tolerancia"


class ReportSummary(BaseModel):
    source: Literal["private", "placeholder"]
    illustrative: bool
    title: str = Field(max_length=200)
    period: str = Field(max_length=120)
    records: int | None = None
    piece_ids: int | None = None
    variables: int | None = None
    nok_definition: str = Field(max_length=400)
    critical_nest: int | None = None
    critical_nest_relative_risk: float | None = None
    relative_risk_basis: str | None = Field(default=None, max_length=400)
    notes: list[str] = Field(default_factory=list, max_length=12)
