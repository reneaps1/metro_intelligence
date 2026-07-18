import type { ChipStatus } from "../../components/ui/StatusChip";
import type { RecommendationState } from "../recommendations/types";
import type { SamplingRecommendationResult } from "./types";

// EXPERIMENTAL (Thompson-Sampling adaptive sampling frequency
// recommender): the frequency number itself is real, engine-computed data
// -- this is display formatting only, never a second computation, so the
// number shown here can never drift out of sync with what the backend
// actually computed.

export type FrequencyStatus = "ok" | "warning" | "nok";

// >20 -> ok (sparse, capable process), 10-20 inclusive -> warning, <10 ->
// nok (tight, unstable process). The number is always rendered as text
// alongside this color (never color-only), same rule RiskHeatmap.tsx
// already follows.
export function frequencyToStatus(frequency: number): FrequencyStatus {
  if (frequency > 20) return "ok";
  if (frequency >= 10) return "warning";
  return "nok";
}

export interface SamplingRecommendationSummary {
  text: string;
  hasConflicts: boolean;
}

export function describeSamplingRecommendation(
  result: SamplingRecommendationResult | null,
): SamplingRecommendationSummary {
  if (result === null) {
    return {
      text: "Adaptive sampling: too little Cpk history to run yet.",
      hasConflicts: false,
    };
  }

  const conflictCount = result.conflicting_recommendations?.length ?? 0;
  if (conflictCount > 0) {
    return {
      text: `Recommended sampling frequency: every ${result.recommended_frequency} pieces. This disagrees with ${conflictCount} existing recommendation${conflictCount > 1 ? "s" : ""} below.`,
      hasConflicts: true,
    };
  }

  return {
    text: `Recommended sampling frequency: every ${result.recommended_frequency} pieces (${result.cpk_trend} trend, confidence ${(result.confidence * 100).toFixed(0)}%).`,
    hasConflicts: false,
  };
}

// Mirrors RecommendationsInboxPage.tsx's own STATE_CHIP status mapping --
// duplicated locally (not imported, since STATE_CHIP isn't exported) so
// this low-blast-radius experimental block doesn't reach into that page's
// internals.
export function recommendationStateToChipStatus(state: RecommendationState): ChipStatus {
  const map: Record<RecommendationState, ChipStatus> = {
    pending: "warning",
    accepted: "ok",
    rejected: "nok",
    superseded: "neutral",
    expired: "neutral",
  };
  return map[state];
}
