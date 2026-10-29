// IQ-F5: mirrors backend/app/schemas/quality_analytics.py.
// IMPORTED = user-uploaded CSV (IQ-F6), analysed as-is, not verified by the platform.
export type DatasetSourceType = "SIMULATED" | "REAL" | "IMPORTED";
export type Granularity = "day" | "hour" | "shift";
export type GroupBy = "cavity" | "machine" | "shift" | "batch" | "mold_cavity";
/** IQ-F10: "spec" = out of tolerance; "reported" = the machine's own verdicts (no limits in the source). */
export type NokBasis = "spec" | "reported";

export interface QualityVariable {
  key: string;
  name: string;
  unit: string;
  /** null when the source only gave limits */
  nominal: number | null;
  lsl: number | null;
  usl: number | null;
}

export interface AvailableFilters {
  machine: boolean;
  cavity: boolean;
  shift: boolean;
  batch: boolean;
  /** IQ-F10 (REAL datasets) */
  mold_cavity?: boolean;
  station?: boolean;
  quality_flags?: boolean;
}

export interface QualityStation {
  key: string;
  name: string;
}

export interface QualityPreset {
  key: string;
  label: string;
  stations: string[];
  group_by: "nest" | "mold_cavity";
}

export interface QualityDataset {
  id: string;
  name: string;
  description: string;
  source_type: DatasetSourceType;
  period_start: string;
  period_end: string;
  pieces: number;
  groups: number;
  variables: QualityVariable[];
  machines: string[];
  cavities: number[];
  shifts: string[];
  batches: string[];
  available_filters: AvailableFilters;
  mechanisms: string[];
  has_reported_verdict: boolean;
  // --- IQ-F10: present on REAL datasets (optional so older payloads still parse) ---
  mold_cavities?: number[];
  stations?: QualityStation[];
  nok_basis?: NokBasis;
  /** Plant local time = UTC + offset; buckets of this dataset already use it. */
  utc_offset_minutes?: number;
  has_groups?: boolean;
  presets?: QualityPreset[];
  /** Counts from the offline conversion report (no identifiers). */
  data_quality?: Record<string, number>;
}

export interface CavityRate {
  cavity: number;
  pieces: number;
  nok: number;
  rate: number | null;
  ci_low: number | null;
  ci_high: number | null;
  relative_risk: number | null;
}

export interface QualitySummary {
  groups: number;
  pieces: number;
  measurements: number;
  ok_pieces: number;
  nok_pieces: number;
  nok_rate: number | null;
  nok_rate_ci: [number, number] | null;
  measurement_nok: number;
  top_variables: string[];
  worst_cavity: CavityRate | null;
  period_start: string | null;
  period_end: string | null;
  nok_definition: string;
  variables_counted: string[];
  variables_with_tolerance: number;
  source_reported: SourceReported | null;
  nok_basis?: NokBasis;
  stations_counted?: string[];
  pieces_without_verdict?: number;
  worst_mold_cavity?: CavityRate | null;
}

/** IQ-F10: NOK pieces attributed to their first failing station (process order). */
export interface StationParetoRow {
  station: string;
  name: string;
  nok: number;
  fails_any: number;
  share: number | null;
  cumulative_pct: number | null;
}

/** IQ-F6: piece verdict carried by the file vs. the one recalculated from spec. */
export interface SourceReported {
  pieces_with_verdict: number;
  nok_pieces: number;
  nok_rate: number | null;
  both_nok: number;
  source_only_nok: number;
  spec_only_nok: number;
  both_ok: number;
  definition: string;
}

export interface TrendBucket {
  bucket: string;
  start: string | null;
  pieces: number;
  nok: number;
  rate: number | null;
}

export interface ParetoRow {
  variable: string;
  name: string;
  nok: number;
  above: number;
  below: number;
  measurements: number;
  cumulative_pct: number | null;
}

export interface HeatmapCell {
  cavity: number;
  variable: string;
  pieces: number;
  nok: number;
  rate: number | null;
}

/** IQ-F18: one observed (nest, mold cavity) combination; absent = never met. */
export interface NestMoldCell {
  nest: number;
  mold_cavity: number;
  pieces: number;
  nok: number;
  rate: number | null;
}

export interface OverviewResponse {
  dataset_id: string;
  source_type: DatasetSourceType;
  granularity: Granularity;
  summary: QualitySummary;
  trend: TrendBucket[];
  pareto: ParetoRow[];
  by_cavity: CavityRate[];
  heatmap: HeatmapCell[];
  by_mold_cavity?: CavityRate[];
  station_pareto?: StationParetoRow[];
  /** "station": heatmap rows are stations (first failing), not variables. */
  heatmap_axis?: "variable" | "station";
  nest_mold?: NestMoldCell[];
}

export interface GroupBox {
  group: string;
  n: number;
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  whisker_low: number;
  whisker_high: number;
  outliers: number;
  mean: number;
  nok: number;
  nok_rate: number;
}

export interface VariableDetailResponse {
  dataset_id: string;
  source_type: DatasetSourceType;
  variable: string;
  name: string;
  spec: { nominal: number | null; lsl: number | null; usl: number | null; unit: string };
  n: number;
  nok: number;
  nok_rate: number | null;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  capability: { cp: number | null; cpk: number | null; reason: string | null } | null;
  control_limits: { center_line: number; ucl: number; lcl: number; engine: string } | null;
  histogram: { x0: number; x1: number; count: number }[];
  /** [epoch ms, value, is_nok] */
  series: [number, number, boolean][];
  series_thinned: boolean;
  group_by: GroupBy;
  groups: GroupBox[];
  cpk_by_day: { day: string; n: number; cpk: number | null }[];
  nok_basis?: NokBasis;
  /** What the NOK markers mean, e.g. "fuera de tolerancia". */
  nok_label?: string;
}

export interface ReportSummary {
  source: "private" | "placeholder";
  illustrative: boolean;
  title: string;
  period: string;
  records: number | null;
  piece_ids: number | null;
  variables: number | null;
  nok_definition: string;
  critical_nest: number | null;
  critical_nest_relative_risk: number | null;
  relative_risk_basis: string | null;
  notes: string[];
}
