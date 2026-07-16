// LM.3/LM.4 (docs/tasks/LM3-live-monitor-presenter-controls.md,
// docs/tasks/LM4-live-monitor-deep-dive.md): typed wrappers built on
// lib/api.ts's apiFetch.
import { apiFetch } from "../api";
import type {
  CapabilityHistoryResponse,
  ScenarioCandidatesResponse,
  ScenarioName,
  SeriesResponse,
} from "./types";

export function getScenarioCandidates(
  scenario: ScenarioName,
  limit: number,
): Promise<ScenarioCandidatesResponse> {
  const params = new URLSearchParams({ scenario, limit: String(limit) });
  return apiFetch(`/characteristics/scenario-candidates?${params.toString()}`);
}

export function getCharacteristicSeries(
  characteristicId: string,
  range: { from?: string; to?: string },
): Promise<SeriesResponse> {
  const params = new URLSearchParams();
  if (range.from) params.set("from", range.from);
  if (range.to) params.set("to", range.to);
  const query = params.toString();
  return apiFetch(`/characteristics/${characteristicId}/series${query ? `?${query}` : ""}`);
}

export function getCapabilityHistory(
  characteristicId: string,
  range: { from?: string; to?: string; windowSize?: number },
): Promise<CapabilityHistoryResponse> {
  const params = new URLSearchParams();
  if (range.from) params.set("from", range.from);
  if (range.to) params.set("to", range.to);
  if (range.windowSize) params.set("window_size", String(range.windowSize));
  const query = params.toString();
  return apiFetch(`/characteristics/${characteristicId}/capability-history${query ? `?${query}` : ""}`);
}
