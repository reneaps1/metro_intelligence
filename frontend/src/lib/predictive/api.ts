import { apiFetch } from "../api";
import type { CusumStudy, FailureStudy, GroupAlarmStudy, ModelLab, PieceRiskStudy, WaveStudy, WhatIfResult } from "./types";

// IQ-F7: single boundary for /api/v1/predictive (demo step 6).

export function fetchModelLab(): Promise<ModelLab> {
  return apiFetch<ModelLab>("/predictive/model-lab");
}

export interface WaveParams {
  machine: string;
  window: number;
  threshold: number;
  horizon: number;
  /** IQ-F12: dataset id (synthetic by default) and NOK target of a REAL dataset. */
  dataset?: string;
  target?: string;
}

export function fetchNokWaves(p: WaveParams): Promise<WaveStudy> {
  const q = new URLSearchParams({
    machine: p.machine,
    window: String(p.window),
    threshold: String(p.threshold),
    horizon: String(p.horizon),
  });
  if (p.dataset) q.set("dataset", p.dataset);
  if (p.target) q.set("target", p.target);
  return apiFetch<WaveStudy>(`/predictive/nok-waves?${q.toString()}`);
}

export function fetchCusum(machine: string, series: string, dataset?: string): Promise<CusumStudy> {
  const q = new URLSearchParams({ machine, series });
  if (dataset) q.set("dataset", dataset);
  return apiFetch<CusumStudy>(`/predictive/cusum?${q.toString()}`);
}

export interface GroupAlarmParams {
  dataset: string;
  grouping: "mold_cavity" | "nest";
  target: string;
  k: number;
  n: number;
  scope: "all" | "after_longest_gap";
}

export function fetchGroupAlarms(p: GroupAlarmParams): Promise<GroupAlarmStudy> {
  const q = new URLSearchParams({
    dataset: p.dataset,
    grouping: p.grouping,
    target: p.target,
    k: String(p.k),
    n: String(p.n),
    scope: p.scope,
  });
  return apiFetch<GroupAlarmStudy>(`/predictive/group-alarms?${q.toString()}`);
}

export function fetchPieceRisk(dataset: string, target: string): Promise<PieceRiskStudy> {
  return apiFetch<PieceRiskStudy>(`/predictive/piece-risk?${new URLSearchParams({ dataset, target }).toString()}`);
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
