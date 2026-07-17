// LM.1 (docs/tasks/LM1-live-monitor-mvp.md): mirrors the two WS event shapes
// `backend/app/api/v1/live_monitor.py` sends (`_serialize_event`). Decimal
// fields come over the wire as strings, same convention as every other
// endpoint (see lib/catalog/types.ts).

export interface PointEvent {
  type: "point";
  characteristic_id: string;
  value: string;
  deviation: string;
  is_ok: boolean;
  measured_at: string;
  rationale: string;
  engine_name: string;
  engine_version: string;
}

export interface ControlLimitsUpdatedEvent {
  type: "control_limits_updated";
  characteristic_id: string;
  cpk: string | null;
  center_line: string;
  ucl: string;
  lcl: string;
  engine_name: string;
  engine_version: string;
}

export type LiveMonitorEvent = PointEvent | ControlLimitsUpdatedEvent;

export type LiveSocketConnectionState = "connecting" | "open" | "reconnecting" | "denied" | "closed";

// LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): sent by the
// client over the same open WebSocket -- mirrors
// `backend/app/api/v1/live_monitor.py`'s `_control_listener`. Silently
// ignored server-side for a role without `live_monitor.update`.
export type ControlMessage =
  | { type: "control"; action: "pause" }
  | { type: "control"; action: "resume" }
  | { type: "control"; action: "set_speed"; speed_multiplier: number };

// Must match backend/app/services/scenario_classifier.py's SCENARIO_NAMES
// (which itself must match seed/config/scenarios.yaml) -- never invent a
// 6th name here.
export const SCENARIO_NAMES = [
  "stable_capable",
  "slow_drift",
  "shift_after_event",
  "high_variance",
  "outlier_nok",
] as const;

export type ScenarioName = (typeof SCENARIO_NAMES)[number];

export interface ScenarioCandidatesResponse {
  scenario: string;
  candidate_pool_size: number;
  characteristic_ids: string[];
}

// LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md): mirrors F4.6's
// `/characteristics/{id}/series` and the new `/capability-history`
// (backend/app/schemas/measurements.py) -- the first real REST consumer of
// this shape in the frontend (F5.7 hasn't wired measurements screens to the
// real API yet, so there's no shared `lib/measurements/` module to reuse).

export interface SpecificationSnapshot {
  id: string;
  nominal: string;
  lower_tol: string | null;
  upper_tol: string | null;
  unit: string;
  valid_from: string;
  valid_to: string | null;
}

export interface SeriesPoint {
  result_id: string;
  measured_at: string;
  value: string;
  deviation: string;
  is_ok: boolean;
  sample_index: number;
  specification: SpecificationSnapshot;
}

export interface SeriesResponse {
  characteristic_id: string;
  unit: string;
  total_points: number;
  returned_points: number;
  downsampled: boolean;
  points: SeriesPoint[];
}

export interface CapabilityWindow {
  window_start: string;
  window_end: string;
  point_count: number;
  cpk: string | null;
  center_line: string | null;
  ucl: string | null;
  lcl: string | null;
  engine_name: string | null;
  engine_version: string | null;
  // The specification this window's rows were actually measured under --
  // NOT necessarily the characteristic's current active spec (a window can
  // close early at a spec-version boundary). Use this, never the current
  // spec's nominal, to convert center_line/ucl/lcl into deviation-space.
  nominal: string | null;
}

export interface CapabilityHistoryResponse {
  characteristic_id: string;
  unit: string;
  window_size: number;
  windows: CapabilityWindow[];
}
