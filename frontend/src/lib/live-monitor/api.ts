// LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): typed wrapper
// around the scenario-candidates lookup, built on lib/api.ts's apiFetch.
import { apiFetch } from "../api";
import type { ScenarioCandidatesResponse, ScenarioName } from "./types";

export function getScenarioCandidates(
  scenario: ScenarioName,
  limit: number,
): Promise<ScenarioCandidatesResponse> {
  const params = new URLSearchParams({ scenario, limit: String(limit) });
  return apiFetch(`/characteristics/scenario-candidates?${params.toString()}`);
}
