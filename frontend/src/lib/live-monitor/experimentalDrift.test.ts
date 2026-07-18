import { describe, expect, it } from "vitest";
import { describeDrift } from "./experimentalDrift";
import type { ExperimentalDriftResult } from "./types";

function driftResult(overrides: Partial<ExperimentalDriftResult> = {}): ExperimentalDriftResult {
  return {
    drift_detected: false,
    drift_direction: null,
    drift_index: null,
    target: "1.50",
    stdev: "0.05",
    k: "0.025",
    h: "0.20",
    points: [],
    rationale: "No sustained drift detected across 10 windows.",
    engine_name: "cusum_drift_engine",
    engine_version: "v1-experimental",
    ...overrides,
  };
}

describe("describeDrift", () => {
  it("reports insufficient data for a null result", () => {
    const summary = describeDrift(null);
    expect(summary.badge).toBe("none");
    expect(summary.text).toMatch(/too little cpk history/i);
  });

  it("passes through the backend rationale verbatim when no drift is detected", () => {
    const result = driftResult({ rationale: "No sustained drift detected across 10 windows." });
    const summary = describeDrift(result);
    expect(summary.badge).toBe("none");
    expect(summary.text).toBe("No sustained drift detected across 10 windows.");
  });

  it("flags the detected badge and surfaces the rationale when drift is detected", () => {
    const result = driftResult({
      drift_detected: true,
      drift_direction: "downward",
      drift_index: 8,
      rationale: "CUSUM drift detected (downward): cumulative deviation crossed the decision threshold.",
    });
    const summary = describeDrift(result);
    expect(summary.badge).toBe("detected");
    expect(summary.text).toContain("downward");
  });
});
