import { apiFetch } from "../api";

// IQ-F13 "Vista A": REAL dimensional pieces joined by time with SIMULATED
// process signals on the same calendar (docs/design/process-quality-join.md).

/** The customer's REAL dataset (local only, plan decision D8): the only source Vista A joins. */
export const REAL_DATASET_ID = "real-dimensional";

export interface ProcessJoinBucket {
  start_ts: number;
  x: number;
  y: number;
  pieces: number;
  cycles: number;
}

export interface ProcessJoinResponse {
  dataset: string;
  scenario_id: string;
  generator_version: string;
  signal: { id: string; name: string; unit: string };
  target: string;
  target_label: string;
  bucket_minutes: number;
  lag_minutes: number;
  utc_offset_minutes: number;
  n: number;
  pearson_r: number | null;
  slope: number | null;
  intercept: number | null;
  r_squared: number | null;
  buckets: ProcessJoinBucket[];
  lag_scan: { lag_minutes: number; r: number | null; n: number }[];
  best_lag_minutes: number | null;
  causal_imposed: boolean;
  provenance: string[];
  notes: string[];
}

export interface ProcessJoinParams {
  dataset: string;
  signal: string;
  target: string;
  bucketMinutes: number;
  lagMinutes: number;
}

export function fetchProcessJoin(p: ProcessJoinParams): Promise<ProcessJoinResponse> {
  const q = new URLSearchParams({
    dataset: p.dataset,
    signal: p.signal,
    target: p.target,
    bucket_minutes: String(p.bucketMinutes),
    lag_minutes: String(p.lagMinutes),
  });
  return apiFetch<ProcessJoinResponse>(`/quality-analytics/process-join?${q.toString()}`);
}

/** Simulated signals offered in Vista A: mold temperature is quality-driven, the rest are controls. */
export const JOIN_SIGNALS: { key: string; label: string }[] = [
  { key: "mold_temp", label: "Temperatura de molde" },
  { key: "holding_pressure", label: "Presión de mantenimiento" },
  { key: "injection_pressure", label: "Presión de inyección (pico)" },
  { key: "cycle_time", label: "Tiempo de ciclo" },
];

export const joinSignalId = (key: string) => `L1.INY-01.${key}`;
