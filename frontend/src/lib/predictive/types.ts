// IQ-F7: mirrors backend/app/schemas/predictive.py.

export interface Confusion {
  tp: number;
  fp: number;
  fn: number;
  tn: number;
}

export interface ModelMetrics {
  key: string;
  name: string;
  family: "ml_tabular" | "deep_learning";
  roc_auc: number;
  pr_auc: number;
  recall: number;
  precision: number;
  confusion: Confusion;
  confusion_approximate: boolean;
  note: string | null;
  test_n: number;
  positives: number;
  flagged: number;
  /** False alarms per NOK piece actually caught (FP / TP). */
  fp_per_tp: number | null;
  alarm_rate: number;
  consistent: boolean;
}

export interface ModelLab {
  source: "private" | "placeholder";
  illustrative: boolean;
  title: string;
  study_date: string;
  dataset_description: string;
  split_description: string;
  variables: number | null;
  test_n: number;
  test_positives: number;
  prevalence: number;
  models: ModelMetrics[];
  best_ml: string | null;
  best_dl: string | null;
  dl_beats_ml: boolean | null;
  has_threshold_results: boolean;
  notes: string[];
}

export type EpisodeStatus = "anticipated" | "detected" | "missed";

export interface WaveStudy {
  source_type: "SIMULATED";
  engine_name: string;
  engine_version: string;
  machine: string;
  window: number;
  threshold: number;
  horizon_groups: number;
  group_interval_min: number;
  rule: string;
  episode_definition: string;
  summary: {
    episodes: number;
    anticipated: number;
    detected: number;
    missed: number;
    mean_delay_min: number | null;
    mean_remaining_share: number | null;
    alert_events: number;
    false_alarm_events: number;
    false_alarms_per_day: number;
  };
  episodes: {
    start: number;
    end: number;
    groups: number;
    status: EpisodeStatus;
    first_alert: number | null;
    delay_min: number | null;
    remaining_share: number | null;
  }[];
  alert_events: { start: number; end: number; false_alarm: boolean }[];
  hours: { ts: number; pieces: number; nok_pieces: number; in_wave: boolean; alert: boolean }[];
}

export interface CusumStudy {
  source_type: "SIMULATED";
  engine_name: string;
  engine_version: string;
  machine: string;
  series: string;
  series_label: string;
  unit: string;
  k_stdevs: number;
  h_stdevs: number;
  target: number | null;
  stdev: number | null;
  k: number | null;
  h: number | null;
  drift_detected: boolean;
  drift_direction: "upward" | "downward" | null;
  drift_ts: number | null;
  rationale: string;
  points: { ts: number; value: number; cusum_high: number; cusum_low: number }[];
}

export interface WhatIfResult {
  source_type: "SIMULATED";
  hypothetical: true;
  hold_pressure_bar: number;
  mold_delta_c: number;
  nest: number | null;
  worn_insert: boolean;
  nominal_mm: number;
  tolerance_mm: number;
  mean_mm: number;
  piece_sd_mm: number;
  nok_probability: number;
  reference_nok_probability: number;
  contributions: { label: string; mm: number }[];
  hold_sweep: { x: number; nok_probability: number }[];
  mold_sweep: { x: number; nok_probability: number }[];
  mechanism: string;
  not_modelled: string[];
}

export interface ThresholdRow {
  threshold: number;
  tp: number;
  fp: number;
  fn: number;
  tn: number;
  precision: number | null;
  recall: number;
  episodes_total: number;
  episodes_anticipated: number;
  mean_lead_h: number | null;
  false_alarms_per_shift: number;
  alert_events: number;
}

export interface FailureEvent {
  hour: number;
  has_precursor: boolean;
  lead_h: number | null;
}

export interface FailureStudy {
  source_type: "SIMULATED";
  engine_name: string;
  engine_version: string;
  horizon_h: number;
  split: {
    description: string;
    train_rows: number;
    test_rows: number;
    train_failures: number;
    test_failures: number;
    test_positive_rate: number;
  };
  features: { key: string; label: string; coefficient: number }[];
  intercept: number;
  model_pr_auc: number;
  thresholds: ThresholdRow[];
  baselines: { key: string; label: string; pr_auc: number; at_half: ThresholdRow }[];
  timeline: {
    machine: string;
    points: { hour: number; score: number; vibration: number; current: number; alarms: number }[];
    failures: FailureEvent[];
    maintenance_h: number[];
  };
  precursor_breakdown: {
    with_precursor_total: number;
    with_precursor_anticipated: number;
    without_precursor_total: number;
    without_precursor_anticipated: number;
  };
  limitations: string[];
}
