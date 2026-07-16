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
