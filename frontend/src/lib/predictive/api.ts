import { apiFetch } from "../api";
import type { CusumStudy, FailureStudy, ModelLab, WaveStudy, WhatIfResult } from "./types";

// IQ-F7: single boundary for /api/v1/predictive (demo step 6).

export function fetchModelLab(): Promise<ModelLab> {
  return apiFetch<ModelLab>("/predictive/model-lab");
}

export interface WaveParams {
  machine: string;
  window: number;
  threshold: number;
  horizon: number;
}

export function fetchNokWaves(p: WaveParams): Promise<WaveStudy> {
  const q = new URLSearchParams({
    machine: p.machine,
    window: String(p.window),
    threshold: String(p.threshold),
    horizon: String(p.horizon),
  });
  return apiFetch<WaveStudy>(`/predictive/nok-waves?${q.toString()}`);
}

export function fetchCusum(machine: string, series: string): Promise<CusumStudy> {
  return apiFetch<CusumStudy>(`/predictive/cusum?${new URLSearchParams({ machine, series }).toString()}`);
}

export interface WhatIfParams {
  holdPressure: number;
  moldDelta: number;
  nest: number | null;
  wornInsert: boolean;
}

export function fetchWhatIf(p: WhatIfParams): Promise<WhatIfResult> {
  const q = new URLSearchParams({
    hold_pressure: String(p.holdPressure),
    mold_delta: String(p.moldDelta),
    worn_insert: String(p.wornInsert),
  });
  if (p.nest !== null) q.set("nest", String(p.nest));
  return apiFetch<WhatIfResult>(`/predictive/what-if?${q.toString()}`);
}

export function fetchFailureStudy(): Promise<FailureStudy> {
  return apiFetch<FailureStudy>("/predictive/failure-study");
}
