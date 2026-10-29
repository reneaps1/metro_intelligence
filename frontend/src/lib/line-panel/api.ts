import { apiFetch } from "../api";
import type { LineMoments, LineReplay } from "./types";

// IQ-F15: single boundary for /api/v1/line-panel (full-screen line quality panel).

export function fetchLineMoments(dataset: string, machine?: string): Promise<LineMoments> {
  const q = new URLSearchParams({ dataset });
  if (machine) q.set("machine", machine);
  return apiFetch<LineMoments>(`/line-panel/moments?${q.toString()}`);
}

export interface ReplayParams {
  dataset: string;
  start: number;
  minutes?: number;
  machine?: string;
}

export function fetchLineReplay(p: ReplayParams): Promise<LineReplay> {
  const q = new URLSearchParams({ dataset: p.dataset, start: String(p.start), minutes: String(p.minutes ?? 60) });
  if (p.machine) q.set("machine", p.machine);
  return apiFetch<LineReplay>(`/line-panel/replay?${q.toString()}`);
}
