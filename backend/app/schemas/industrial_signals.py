"""IQ-F2: response models for the simulated industrial-signals API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SourceType = Literal["SIMULATED"]


class SignalInfo(BaseModel):
    signal_id: str
    key: str
    machine_code: str
    name: str
    unit: str
    value_type: Literal["analog", "digital", "discrete", "counter"]
    sampling: Literal["profile", "continuous", "per_cycle", "state"]
    rate_hz: float | None
    informative: bool
    description: str
    source_type: SourceType
    causal_imposed: bool


class SignalTreeNode(BaseModel):
    id: str
    name: str
    node_type: Literal["plant", "area", "line", "machine", "group", "signal"]
    children: list[SignalTreeNode]
    signal: SignalInfo | None


class SignalTreeResponse(BaseModel):
    source_type: SourceType
    generator_version: str
    root: SignalTreeNode


class ScenarioOut(BaseModel):
    id: str
    name: str
    description: str
    start: datetime
    end: datetime
    event_count: int


class ScenarioListResponse(BaseModel):
    source_type: SourceType
    generator_version: str
    items: list[ScenarioOut]


class SignalSeries(BaseModel):
    signal_id: str
    name: str
    unit: str
    value_type: str
    sampling: str
    native_points: int
    returned_points: int
    downsampled: bool
    mode: Literal["raw", "envelope"]
    # [epoch milliseconds, value] pairs -- compact on purpose (payload size).
    points: list[tuple[int, float]]


class SeriesResponse(BaseModel):
    scenario_id: str
    source_type: SourceType
    generator_version: str
    start: datetime
    end: datetime
    series: list[SignalSeries]


class ProcessEventOut(BaseModel):
    id: str
    scenario_id: str
    machine_code: str
    event_type: str
    label: str
    severity: Literal["info", "warning", "critical"]
    start: datetime
    end: datetime | None
    signal_ids: list[str]


class ProcessEventListResponse(BaseModel):
    scenario_id: str
    source_type: SourceType
    items: list[ProcessEventOut]


class CorrelationSignal(BaseModel):
    signal_id: str
    name: str
    unit: str
    causal_imposed: bool


class LagScoreOut(BaseModel):
    lag: float
    n: int
    pearson_r: float | None


class CorrelationResponse(BaseModel):
    scenario_id: str
    source_type: SourceType
    generator_version: str
    x: CorrelationSignal
    y: CorrelationSignal
    mode: Literal["time", "cycle"]
    lag: float
    lag_unit: Literal["s", "cycles"]
    start: datetime
    end: datetime
    n: int
    pearson_r: float | None
    slope: float | None
    intercept: float | None
    r_squared: float | None
    # [x, y] scatter pairs, evenly thinned for the browser.
    points: list[tuple[float, float]]
    lag_scan: list[LagScoreOut]
    best_lag: float | None
    causal_imposed: bool
