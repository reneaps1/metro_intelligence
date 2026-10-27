"""IQ-F7: request/response models for the predictive lab (demo step 6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# Model lab: PRECOMPUTED results of a historical ML/DL study
# --------------------------------------------------------------------------- #


class Confusion(BaseModel):
    tp: int = Field(ge=0)
    fp: int = Field(ge=0)
    fn: int = Field(ge=0)
    tn: int = Field(ge=0)


class ModelResultIn(BaseModel):
    """One model as written in the study file (private or placeholder)."""

    key: str = Field(max_length=32)
    name: str = Field(max_length=80)
    family: Literal["ml_tabular", "deep_learning"]
    roc_auc: float = Field(ge=0, le=1)
    pr_auc: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    precision: float = Field(ge=0, le=1)
    confusion: Confusion
    # True when the matrix was reconstructed from the reported recall/precision.
    confusion_approximate: bool = False
    note: str | None = Field(default=None, max_length=300)


class ModelLabIn(BaseModel):
    title: str = Field(max_length=200)
    study_date: str = Field(max_length=60)
    dataset_description: str = Field(max_length=400)
    split_description: str = Field(max_length=400)
    variables: int | None = None
    models: list[ModelResultIn] = Field(min_length=1, max_length=8)
    notes: list[str] = Field(default_factory=list, max_length=12)


class ModelMetrics(ModelResultIn):
    """Reported metrics plus figures derived from the confusion matrix."""

    test_n: int
    positives: int
    flagged: int
    # False alarms raised per NOK piece actually caught (FP / TP).
    fp_per_tp: float | None
    # Share of the test pieces the model would send to review.
    alarm_rate: float
    # The reported recall/precision match the matrix (±0.5 points).
    consistent: bool


class ModelLab(BaseModel):
    source: Literal["private", "placeholder"]
    illustrative: bool
    title: str
    study_date: str
    dataset_description: str
    split_description: str
    variables: int | None
    test_n: int
    test_positives: int
    prevalence: float
    models: list[ModelMetrics]
    best_ml: str | None
    best_dl: str | None
    # Compared on PR-AUC (the metric that matters with ~0.5 % NOK); None if a family is missing.
    dl_beats_ml: bool | None
    # Per-threshold results were not delivered: no interactive threshold, no ROC/PR curves.
    has_threshold_results: bool
    notes: list[str]


# --------------------------------------------------------------------------- #
# NOK waves: persistence rule vs. known synthetic episodes
# --------------------------------------------------------------------------- #

SourceType = Literal["SIMULATED"]


class WaveEpisodeOut(BaseModel):
    start: float
    end: float
    groups: int
    status: Literal["anticipated", "detected", "missed"]
    first_alert: float | None
    # Minutes from the wave start to the first alert (negative = before the start).
    delay_min: float | None
    remaining_share: float | None


class AlertEventOut(BaseModel):
    start: float
    end: float
    false_alarm: bool


class WaveHourOut(BaseModel):
    ts: float
    pieces: int
    nok_pieces: int
    in_wave: bool
    alert: bool


class WaveSummary(BaseModel):
    episodes: int
    anticipated: int
    detected: int
    missed: int
    mean_delay_min: float | None
    mean_remaining_share: float | None
    alert_events: int
    false_alarm_events: int
    false_alarms_per_day: float


class WaveStudyResponse(BaseModel):
    source_type: SourceType = "SIMULATED"
    engine_name: str
    engine_version: str
    machine: str
    window: int
    threshold: int
    horizon_groups: int
    group_interval_min: float
    rule: str
    episode_definition: str
    summary: WaveSummary
    episodes: list[WaveEpisodeOut]
    alert_events: list[AlertEventOut]
    hours: list[WaveHourOut]


# --------------------------------------------------------------------------- #
# CUSUM over an hourly series of the synthetic dataset
# --------------------------------------------------------------------------- #


class CusumPointOut(BaseModel):
    ts: float
    value: float
    cusum_high: float
    cusum_low: float


class CusumResponse(BaseModel):
    source_type: SourceType = "SIMULATED"
    engine_name: str
    engine_version: str
    machine: str
    series: str
    series_label: str
    unit: str
    k_stdevs: float
    h_stdevs: float
    # None when the series is too short or constant (nothing meaningful to say).
    target: float | None
    stdev: float | None
    k: float | None
    h: float | None
    drift_detected: bool
    drift_direction: Literal["upward", "downward"] | None
    drift_ts: float | None
    rationale: str
    points: list[CusumPointOut]


# --------------------------------------------------------------------------- #
# What-if over the Vista B synthetic mechanism (HYPOTHETICAL)
# --------------------------------------------------------------------------- #


class ContributionOut(BaseModel):
    label: str
    mm: float


class SweepPointOut(BaseModel):
    x: float
    nok_probability: float


class WhatIfResponse(BaseModel):
    source_type: SourceType = "SIMULATED"
    hypothetical: bool = True
    hold_pressure_bar: float
    mold_delta_c: float
    nest: int | None
    worn_insert: bool
    nominal_mm: float
    tolerance_mm: float
    mean_mm: float
    piece_sd_mm: float
    nok_probability: float
    reference_nok_probability: float
    contributions: list[ContributionOut]
    hold_sweep: list[SweepPointOut]
    mold_sweep: list[SweepPointOut]
    mechanism: str
    not_modelled: list[str]


# --------------------------------------------------------------------------- #
# F7.b: experimental machine-failure prediction on a simulated history
# --------------------------------------------------------------------------- #

_attrs = ConfigDict(from_attributes=True, protected_namespaces=())


class FailureEventOut(BaseModel):
    model_config = _attrs
    hour: int
    has_precursor: bool
    lead_h: int | None


class StudySplitOut(BaseModel):
    model_config = _attrs
    description: str
    train_rows: int
    test_rows: int
    train_failures: int
    test_failures: int
    test_positive_rate: float


class FeatureWeightOut(BaseModel):
    model_config = _attrs
    key: str
    label: str
    coefficient: float


class ThresholdRowOut(BaseModel):
    model_config = _attrs
    threshold: float
    tp: int
    fp: int
    fn: int
    tn: int
    precision: float | None
    recall: float
    episodes_total: int
    episodes_anticipated: int
    mean_lead_h: float | None
    false_alarms_per_shift: float
    alert_events: int


class BaselineOut(BaseModel):
    model_config = _attrs
    key: str
    label: str
    pr_auc: float
    at_half: ThresholdRowOut


class TimelinePointOut(BaseModel):
    model_config = _attrs
    hour: int
    score: float
    vibration: float
    current: float
    alarms: int


class StudyTimelineOut(BaseModel):
    model_config = _attrs
    machine: str
    points: list[TimelinePointOut]
    failures: list[FailureEventOut]
    maintenance_h: list[int]


class PrecursorBreakdownOut(BaseModel):
    model_config = _attrs
    with_precursor_total: int
    with_precursor_anticipated: int
    without_precursor_total: int
    without_precursor_anticipated: int


class FailureStudyResponse(BaseModel):
    model_config = _attrs
    source_type: SourceType = "SIMULATED"
    engine_name: str
    engine_version: str
    horizon_h: int
    split: StudySplitOut
    features: list[FeatureWeightOut]
    intercept: float
    model_pr_auc: float
    thresholds: list[ThresholdRowOut]
    baselines: list[BaselineOut]
    timeline: StudyTimelineOut
    precursor_breakdown: PrecursorBreakdownOut
    limitations: list[str]
