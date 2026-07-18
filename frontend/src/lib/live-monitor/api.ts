// LM.3/LM.4 (docs/tasks/LM3-live-monitor-presenter-controls.md,
// docs/tasks/LM4-live-monitor-deep-dive.md): typed wrappers built on
// lib/api.ts's apiFetch.
import { apiFetch } from "../api";
import type {
  Alert,
  AlertsPage,
  CapabilityHistoryResponse,
  ExperimentalDriftResult,
  SamplingRecommendationResult,
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

// Phase 13 preview (CLAUDE.md §22) -- shadow-mode, read-only, same RBAC as
// getCapabilityHistory (no new permission).
export function getExperimentalDrift(
  characteristicId: string,
  range: { from?: string; to?: string; windowSize?: number },
): Promise<ExperimentalDriftResult | null> {
  const params = new URLSearchParams();
  if (range.from) params.set("from", range.from);
  if (range.to) params.set("to", range.to);
  if (range.windowSize) params.set("window_size", String(range.windowSize));
  const query = params.toString();
  return apiFetch(`/characteristics/${characteristicId}/experimental-drift${query ? `?${query}` : ""}`);
}

// EXPERIMENTAL (Thompson-Sampling adaptive sampling frequency recommender)
// -- shadow-mode, read-only, same RBAC as getCapabilityHistory (no new
// permission). Unlike getExperimentalDrift, this always returns a body
// (never null) -- insufficient history is a conservative-default body, not
// a null response.
export function getSamplingRecommendation(
  characteristicId: string,
  range: { from?: string; to?: string; windowSize?: number },
): Promise<SamplingRecommendationResult> {
  const params = new URLSearchParams();
  if (range.from) params.set("from", range.from);
  if (range.to) params.set("to", range.to);
  if (range.windowSize) params.set("window_size", String(range.windowSize));
  const query = params.toString();
  return apiFetch(`/characteristics/${characteristicId}/sampling-recommendation${query ? `?${query}` : ""}`);
}

// Live Monitor alarm fix (2026-07).
export function getAlerts(params: {
  characteristicId?: string;
  state?: "open" | "acknowledged";
}): Promise<AlertsPage> {
  const query = new URLSearchParams();
  if (params.characteristicId) query.set("characteristic_id", params.characteristicId);
  if (params.state) query.set("state", params.state);
  const qs = query.toString();
  return apiFetch(`/alerts${qs ? `?${qs}` : ""}`);
}

export function acknowledgeAlert(alertId: string): Promise<Alert> {
  return apiFetch(`/alerts/${alertId}/acknowledge`, { method: "POST" });
}
