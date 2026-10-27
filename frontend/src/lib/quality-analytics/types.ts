// IQ-F5: mirrors backend/app/schemas/quality_analytics.py.
export type DatasetSourceType = "SIMULATED" | "REAL";
export type Granularity = "day" | "hour" | "shift";
export type GroupBy = "cavity" | "machine" | "shift" | "batch";

export interface QualityVariable {
  key: string;
  name: string;
  unit: string;
  nominal: number;
  lsl: number | null;
  usl: number | null;
}

export interface AvailableFilters {
  machine: boolean;
  cavity: boolean;
  shift: boolean;
  batch: boolean;
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

export interface OverviewResponse {
  dataset_id: string;
  source_type: DatasetSourceType;
  granularity: Granularity;
  summary: QualitySummary;
  trend: TrendBucket[];
  pareto: ParetoRow[];
  by_cavity: CavityRate[];
  heatmap: HeatmapCell[];
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
  spec: { nominal: number; lsl: number | null; usl: number | null; unit: string };
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
