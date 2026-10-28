"""IQ-F14: response models for the line quality panel (`docs/design/line-quality-panel.md`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Provenance = Literal["REAL", "SIMULATED"]
RuleKey = Literal["R1", "R2", "R3", "R4"]


class MomentOut(BaseModel):
    key: str
    kind: Literal["stop", "attention", "normal"]
    rule: RuleKey | None
    # Nest of an R2 event; None otherwise.
    key_group: int | None
    raised_ts: float
    # Streak length (R1), ratio (R2), rate (R3) or stretch length in pieces (normal).
    peak: float
    label: str
    replay_start_ts: float


class MomentsResponse(BaseModel):
    dataset: str
    dataset_name: str
    provenance: Provenance
    utc_offset_minutes: int
    start_ts: float
    end_ts: float
    pieces: int
    reference_nok_rate: float
    engine_name: str
    engine_version: str
    moments: list[MomentOut]


class StationOut(BaseModel):
    key: str
    name: str


class LineOut(BaseModel):
    nests: list[int]
    # Number of mold cavities; None when the dataset has none (R4 does not apply).
    mold_cavities: int | None
    stations: list[StationOut]


class RuleTexts(BaseModel):
    R1: str
    R2: str
    R3: str
    R4: str


class RulesOut(BaseModel):
    run_limit: int
    nest_window: int
    nest_factor: float
    nest_min_nok: int
    rate_window: int
    rate_factor: float
    rate_limit: float
    cavity_window: int
    cavity_factor: float
    cavity_limit: float
    reference_nok_rate: float
    clear_fraction: float
    texts: RuleTexts


class WindowOut(BaseModel):
    start_ts: float
    end_ts: float


class ShiftOut(BaseModel):
    label: str
    start_ts: float
    end_ts: float


class BaselineOut(BaseModel):
    pieces: int
    nok: int
    by_nest: list[tuple[int, int, int]]  # [nest, pieces, nok]
    by_cavity: list[tuple[int, int, int]]  # [mold cavity, pieces, nok]
    by_station: list[tuple[str, int]]  # [station key, NOK pieces it failed first]
    hours: list[tuple[float, int, int]]  # [hour start (epoch), pieces, nok]


class PiecesOut(BaseModel):
    t: list[float]
    nest: list[int | None]
    cavity: list[int | None]
    nok: list[int]  # 1 = NOK, 0 = OK
    station: list[int]


class StateOut(BaseModel):
    run: list[int]
    rate: list[float | None]
    nest_ratio: list[float | None]
    nest_ratio_nest: list[int | None]
    cavity_rate: list[float | None]
    cavity_worst: list[int | None]


class AlarmOut(BaseModel):
    id: str
    rule: RuleKey
    priority: int
    key: int | None
    raised_index: int
    raised_ts: float
    cleared_index: int | None
    cleared_ts: float | None
    evidence_from_index: int
    evidence_from_ts: float
    value: float
    peak: float
    limit: float
    nests: list[int]
    station: str | None


class ReplayResponse(BaseModel):
    engine_name: str
    engine_version: str
    dataset: str
    dataset_name: str
    provenance: Provenance
    nok_basis: Literal["reported", "spec"]
    utc_offset_minutes: int
    machine: str | None
    line: LineOut
    rules: RulesOut
    window: WindowOut
    lead: int
    shifts: list[ShiftOut]
    baseline: BaselineOut
    pieces: PiecesOut
    state: StateOut
    alarms: list[AlarmOut]
