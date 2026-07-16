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
