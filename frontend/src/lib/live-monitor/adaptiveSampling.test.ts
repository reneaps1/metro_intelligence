import { describe, expect, it } from "vitest";
import {
  describeSamplingRecommendation,
  frequencyToStatus,
  recommendationStateToChipStatus,
} from "./adaptiveSampling";
import type { SamplingRecommendationResult } from "./types";

function result(overrides: Partial<SamplingRecommendationResult> = {}): SamplingRecommendationResult {
  return {
    characteristic_id: "11111111-1111-1111-1111-111111111111",
    recommended_frequency: 20,
    current_cpk: 1.8,
    cpk_trend: "stable",
    confidence: 0.75,
    windows_analyzed: 8,
    conflicting_recommendations: null,
    ...overrides,
  };
}

describe("frequencyToStatus", () => {
  it("returns ok above 20", () => {
    expect(frequencyToStatus(21)).toBe("ok");
    expect(frequencyToStatus(100)).toBe("ok");
  });

  it("returns warning between 10 and 20 inclusive", () => {
    expect(frequencyToStatus(10)).toBe("warning");
    expect(frequencyToStatus(15)).toBe("warning");
    expect(frequencyToStatus(20)).toBe("warning");
  });

  it("returns nok below 10", () => {
    expect(frequencyToStatus(9)).toBe("nok");
    expect(frequencyToStatus(5)).toBe("nok");
  });
});

describe("describeSamplingRecommendation", () => {
  it("reports insufficient data for a null result", () => {
    const summary = describeSamplingRecommendation(null);
    expect(summary.text).toMatch(/too little Cpk history/i);
    expect(summary.hasConflicts).toBe(false);
  });

  it("summarizes a result with no conflicts", () => {
    const summary = describeSamplingRecommendation(result());
    expect(summary.text).toContain("every 20 pieces");
    expect(summary.hasConflicts).toBe(false);
  });

  it("mentions the conflict count when conflicts are present", () => {
    const summary = describeSamplingRecommendation(
      result({
        conflicting_recommendations: [
          {
            id: "c1",
            type: "frequency_increase",
            status: "pending",
            title: "Frequency increase",
            reason: "Trend approaching tolerance.",
            conflict_reason: "Asks for tighter inspection.",
          },
        ],
      }),
    );
    expect(summary.hasConflicts).toBe(true);
    expect(summary.text).toContain("1 existing recommendation");
  });
});

describe("recommendationStateToChipStatus", () => {
  it("maps pending to warning", () => {
    expect(recommendationStateToChipStatus("pending")).toBe("warning");
  });

  it("maps accepted to ok", () => {
    expect(recommendationStateToChipStatus("accepted")).toBe("ok");
  });

  it("maps rejected to nok", () => {
    expect(recommendationStateToChipStatus("rejected")).toBe("nok");
  });

  it("maps superseded and expired to neutral", () => {
    expect(recommendationStateToChipStatus("superseded")).toBe("neutral");
    expect(recommendationStateToChipStatus("expired")).toBe("neutral");
  });
});
