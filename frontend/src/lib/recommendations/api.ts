// F5.9 (MI-38): typed wrappers around F4.8's /recommendations and
// /decisions endpoints, built on lib/api.ts's apiFetch.
import { apiFetch } from "../api";
import type {
  ActionTaken,
  ActionTakenCreateInput,
  DecisionAction,
  DecisionResult,
  Page,
  Recommendation,
  RecommendationDetail,
  RecommendationState,
} from "./types";

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export function listRecommendations(params: {
  state?: RecommendationState;
  characteristicId?: string;
  page?: number;
}): Promise<Page<Recommendation>> {
  return apiFetch(
    `/recommendations${query({
      state: params.state,
      characteristic_id: params.characteristicId,
      page: params.page,
      page_size: 100,
    })}`,
  );
}

export function getRecommendation(id: string): Promise<RecommendationDetail> {
  return apiFetch(`/recommendations/${id}`);
}

export function decideRecommendation(
  id: string,
  action: DecisionAction,
  comment: string,
): Promise<DecisionResult> {
  return apiFetch(`/recommendations/${id}/decision`, {
    method: "POST",
    body: JSON.stringify({ action, comment }),
  });
}

export function recordActionTaken(decisionId: string, payload: ActionTakenCreateInput): Promise<ActionTaken> {
  return apiFetch(`/decisions/${decisionId}/actions`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
