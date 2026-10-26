import { apiFetch } from "../api";
import type {
  ProcessEventListResponse,
  ScenarioListResponse,
  SeriesResponse,
  SignalTreeNode,
  SignalTreeResponse,
} from "./types";

// IQ-F2: single boundary for the simulated industrial-signals API. A real
// PLC/iba source would implement the same contract server-side.

export function fetchSignalTree(): Promise<SignalTreeResponse> {
  return apiFetch<SignalTreeResponse>("/industrial-signals/tree");
}

export function fetchScenarios(): Promise<ScenarioListResponse> {
  return apiFetch<ScenarioListResponse>("/industrial-signals/scenarios");
}

export function fetchProcessEvents(scenarioId: string): Promise<ProcessEventListResponse> {
  const params = new URLSearchParams({ scenario: scenarioId });
  return apiFetch<ProcessEventListResponse>(`/industrial-signals/events?${params.toString()}`);
}

export interface SeriesQuery {
  scenarioId: string;
  signalIds: string[];
  start?: string;
  end?: string;
  maxPoints?: number;
}

export function fetchSeries({ scenarioId, signalIds, start, end, maxPoints }: SeriesQuery): Promise<SeriesResponse> {
  const params = new URLSearchParams({ scenario: scenarioId, signals: signalIds.join(",") });
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  if (maxPoints) params.set("max_points", String(maxPoints));
  return apiFetch<SeriesResponse>(`/industrial-signals/series?${params.toString()}`);
}

/** Signal leaves under a node, depth-first. */
export function collectSignals(node: SignalTreeNode): SignalTreeNode[] {
  if (node.node_type === "signal") return [node];
  return node.children.flatMap(collectSignals);
}
