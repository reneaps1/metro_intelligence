import type { ExperimentalDriftResult } from "./types";

// Phase 13 preview (CLAUDE.md §22, §16): the CUSUM math runs server-side
// (app.engines.experimental_ml.drift_cusum) -- this is display formatting
// only, never a second computation, so the number shown here can never
// drift out of sync with what the backend actually computed.
export interface ExperimentalDriftSummary {
  text: string;
  badge: "detected" | "none";
}

export function describeDrift(result: ExperimentalDriftResult | null): ExperimentalDriftSummary {
  if (result === null) {
    return {
      text: "Experimental drift detector: too little Cpk history to run yet.",
      badge: "none",
    };
  }

  return {
    text: result.rationale,
    badge: result.drift_detected ? "detected" : "none",
  };
}
