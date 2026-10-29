// IQ-F15: contract of /api/v1/line-panel (docs/design/line-quality-panel.md).

export type RuleId = "R1" | "R2" | "R3" | "R4";
/** 1 = diamond (stop), 2 = triangle, 3 = advisory (square, no stop). */
export type LinePriority = 1 | 2 | 3;
export type MomentKind = "stop" | "attention" | "normal";

export interface LineMoment {
  key: string;
  kind: MomentKind;
  rule: RuleId | null;
  key_group: number | null;
  raised_ts: number;
  peak: number;
  label: string;
  replay_start_ts: number;
}

export interface LineMoments {
  dataset: string;
  dataset_name: string;
  provenance: "REAL" | "SIMULATED";
  utc_offset_minutes: number;
  start_ts: number;
  end_ts: number;
  pieces: number;
  reference_nok_rate: number;
  engine_name: string;
  engine_version: string;
  moments: LineMoment[];
}

export interface LineRules {
  run_limit: number;
  nest_window: number;
  nest_factor: number;
  nest_min_nok: number;
  rate_window: number;
  rate_factor: number;
  rate_limit: number;
  cavity_window: number;
  cavity_factor: number;
  cavity_limit: number;
  reference_nok_rate: number;
  /** Deadband: an open R2–R4 alarm clears only below this share of its limit. */
  clear_fraction: number;
  texts: Record<RuleId, string>;
}

export interface LineShift {
  label: string;
  start_ts: number;
  end_ts: number;
}

export interface LineAlarmEvent {
  id: string;
  rule: RuleId;
  priority: LinePriority;
  key: number | null;
  raised_index: number;
  raised_ts: number;
  cleared_index: number | null;
  cleared_ts: number | null;
  evidence_from_index: number;
  evidence_from_ts: number;
  value: number;
  peak: number;
  limit: number;
  nests: number[];
  station: string | null;
}

export interface LineReplay {
  engine_name: string;
  engine_version: string;
  dataset: string;
  dataset_name: string;
  provenance: "REAL" | "SIMULATED";
  nok_basis: "reported" | "spec";
  utc_offset_minutes: number;
  machine: string | null;
  line: { nests: number[]; mold_cavities: number | null; stations: { key: string; name: string }[] };
  rules: LineRules;
  window: { start_ts: number; end_ts: number };
  lead: number;
  shifts: LineShift[];
  baseline: {
    pieces: number;
    nok: number;
    /** [group, pieces, nok] */
    by_nest: [number, number, number][];
    by_cavity: [number, number, number][];
    /** [station key, nok] by first failing station */
    by_station: [string, number][];
    /** [hour start epoch s, pieces, nok] */
    hours: [number, number, number][];
  };
  pieces: { t: number[]; nest: (number | null)[]; cavity: (number | null)[]; nok: number[]; station: number[] };
  state: {
    run: number[];
    rate: (number | null)[];
    nest_ratio: (number | null)[];
    nest_ratio_nest: (number | null)[];
    cavity_rate: (number | null)[];
    cavity_worst: (number | null)[];
  };
  alarms: LineAlarmEvent[];
}
