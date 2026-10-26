// IQ-F2: mirrors backend/app/schemas/industrial_signals.py.
export type SignalSourceType = "SIMULATED";

export interface SignalInfo {
  signal_id: string;
  key: string;
  machine_code: string;
  name: string;
  unit: string;
  value_type: "analog" | "digital" | "discrete" | "counter";
  sampling: "profile" | "continuous" | "per_cycle" | "state";
  rate_hz: number | null;
  informative: boolean;
  description: string;
  source_type: SignalSourceType;
}

export interface SignalTreeNode {
  id: string;
  name: string;
  node_type: "plant" | "area" | "line" | "machine" | "group" | "signal";
  children: SignalTreeNode[];
  signal: SignalInfo | null;
}

export interface SignalTreeResponse {
  source_type: SignalSourceType;
  generator_version: string;
  root: SignalTreeNode;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  start: string;
  end: string;
  event_count: number;
}

export interface ScenarioListResponse {
  source_type: SignalSourceType;
  generator_version: string;
  items: Scenario[];
}

export interface SignalSeries {
  signal_id: string;
  name: string;
  unit: string;
  value_type: string;
  sampling: string;
  native_points: number;
  returned_points: number;
  downsampled: boolean;
  mode: "raw" | "envelope";
  /** [epoch ms, value] */
  points: [number, number][];
}

export interface SeriesResponse {
  scenario_id: string;
  source_type: SignalSourceType;
  generator_version: string;
  start: string;
  end: string;
  series: SignalSeries[];
}

export type ProcessEventSeverity = "info" | "warning" | "critical";

export interface ProcessEvent {
  id: string;
  scenario_id: string;
  machine_code: string;
  event_type: string;
  label: string;
  severity: ProcessEventSeverity;
  start: string;
  end: string | null;
  signal_ids: string[];
}

export interface ProcessEventListResponse {
  scenario_id: string;
  source_type: SignalSourceType;
  items: ProcessEvent[];
}
