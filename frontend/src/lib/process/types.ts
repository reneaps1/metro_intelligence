// Per-step process views (ADR-005). Mirrors backend/app/schemas/process.py:
// snake_case, decimals from the specification as strings, statistics as numbers.

export type StepStatus = "ok" | "warning" | "critical" | "neutral";
export type OperationKind = "electrical" | "pin_length" | "pin_position" | "type_check";

export interface Operation {
  id: string;
  code: string;
  name: string;
  kind: OperationKind;
  side: "pcb" | "connector" | null;
  sequence: number;
}

export interface Line {
  id: string;
  code: string;
  name: string;
  operations: Operation[];
}

export interface Recipe {
  id: string;
  code: number;
  label: string;
  variant_part_number: string | null;
  variant_pending: boolean;
}

export interface DateRange {
  start: string;
  end: string;
  first_available: string | null;
  last_available: string | null;
}

export interface DailyCount {
  day: string;
  pieces: number;
  machine_nok: number;
  spec_nok: number;
}

export interface StepOverview {
  operation: Operation;
  pieces: number;
  machine_nok: number;
  machine_nok_rate: number | null;
  spec_nok: number;
  spec_nok_rate: number | null;
  first_pass_yield: number | null;
  repeat_attempts: number;
  has_specification: boolean;
  worst_cpk: number | null;
  disagreements: number;
  coverage: number | null;
  status: StepStatus;
  trend: DailyCount[];
}

export interface LineOverview {
  line: Line;
  range: DateRange;
  recipes: Recipe[];
  selected_recipe_ids: string[];
  reference_pieces: number;
  steps: StepOverview[];
}

export interface SpecLimits {
  nominal: string;
  lower_tol: string | null;
  upper_tol: string | null;
  lower_limit: string | null;
  upper_limit: string | null;
}

export interface CharacteristicSummary {
  id: string;
  code: string;
  name: string;
  unit: string;
  n: number;
  mean: number | null;
  std_dev: number | null;
  min: number | null;
  max: number | null;
  machine_nok: number;
  spec_nok: number;
  machine_ok_spec_nok: number;
  specification: SpecLimits | null;
  cp: number | null;
  cpk: number | null;
  capability_kind: "Cpk" | "Cpu" | "Cpl" | null;
}

export interface BreakdownRow {
  key: string;
  label: string;
  pieces: number;
  machine_nok: number;
  spec_nok: number;
}

export interface OperationSummary {
  operation: Operation;
  range: DateRange;
  pieces: number;
  machine_nok: number;
  spec_nok: number;
  repeat_attempts: number;
  disagreements: number;
  status: StepStatus;
  characteristics: CharacteristicSummary[];
  by_recipe: BreakdownRow[];
  by_nest: BreakdownRow[];
  trend: DailyCount[];
}

export interface HistogramBin {
  lower: number;
  upper: number;
  count: number;
}

export interface CharacteristicDailyPoint {
  day: string;
  n: number;
  mean: number;
  min: number;
  max: number;
  spec_nok: number;
  machine_nok: number;
  cpk: number | null;
}

export interface CharacteristicDetail {
  characteristic: CharacteristicSummary;
  range: DateRange;
  bins: HistogramBin[];
  below_range: number;
  above_range: number;
  daily: CharacteristicDailyPoint[];
}

export interface TraceValue {
  characteristic_id: string;
  code: string;
  name: string;
  unit: string;
  value: string;
  machine_ok: boolean | null;
  is_ok: boolean | null;
  deviation: string | null;
  specification: SpecLimits | null;
}

export interface TraceStep {
  operation: Operation;
  attempt: number;
  recorded_at: string;
  nest: number | null;
  program_number: number | null;
  machine_ok: boolean | null;
  values: TraceValue[];
}

export interface PieceTrace {
  serial_number: string;
  line: Line;
  recipe: Recipe | null;
  first_seen_at: string;
  steps: TraceStep[];
}

export interface ProcessFilters {
  from?: string;
  to?: string;
  recipeIds: string[];
}
