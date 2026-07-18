import { describe, expect, it } from "vitest";
import { summarizeCapabilityTrend } from "./capabilityTrend";
import type { CapabilityWindow } from "./types";

function window(overrides: Partial<CapabilityWindow> = {}): CapabilityWindow {
  return {
    window_start: "2026-01-01T00:00:00Z",
    window_end: "2026-01-02T00:00:00Z",
    point_count: 20,
    cpk: "1.80",
    center_line: "10.00",
    ucl: "10.10",
    lcl: "9.90",
    engine_name: "spc_engine",
    engine_version: "v1",
    nominal: "10.00",
    ...overrides,
  };
}

describe("summarizeCapabilityTrend", () => {
  it("reports insufficient data with zero windows", () => {
    const result = summarizeCapabilityTrend([]);
    expect(result.direction).toBe("insufficient_data");
    expect(result.approachingThreshold).toBe(false);
  });

  it("reports insufficient data with only one window with a defined Cpk", () => {
    const result = summarizeCapabilityTrend([window({ window_start: "2026-01-01T00:00:00Z" })]);
    expect(result.direction).toBe("insufficient_data");
  });

  it("reports insufficient data when all windows have a null Cpk", () => {
    const result = summarizeCapabilityTrend([
      window({ window_start: "2026-01-01T00:00:00Z", cpk: null }),
      window({ window_start: "2026-01-02T00:00:00Z", cpk: null }),
    ]);
    expect(result.direction).toBe("insufficient_data");
  });

  it("detects a declining sequence, in chronological order regardless of input order", () => {
    const windows = [
      window({ window_start: "2026-01-03T00:00:00Z", cpk: "1.10" }),
      window({ window_start: "2026-01-01T00:00:00Z", cpk: "1.80" }),
      window({ window_start: "2026-01-02T00:00:00Z", cpk: "1.40" }),
    ];

    const result = summarizeCapabilityTrend(windows);
    expect(result.direction).toBe("declining");
    expect(result.text).toContain("1.80 → 1.40 → 1.10");
  });

  it("detects an improving sequence", () => {
    const windows = [
      window({ window_start: "2026-01-01T00:00:00Z", cpk: "1.00" }),
      window({ window_start: "2026-01-02T00:00:00Z", cpk: "1.40" }),
      window({ window_start: "2026-01-03T00:00:00Z", cpk: "1.80" }),
    ];

    const result = summarizeCapabilityTrend(windows);
    expect(result.direction).toBe("improving");
    expect(result.approachingThreshold).toBe(false);
  });

  it("detects a stable (non-monotonic) sequence", () => {
    const windows = [
      window({ window_start: "2026-01-01T00:00:00Z", cpk: "1.50" }),
      window({ window_start: "2026-01-02T00:00:00Z", cpk: "1.55" }),
      window({ window_start: "2026-01-03T00:00:00Z", cpk: "1.52" }),
    ];

    const result = summarizeCapabilityTrend(windows);
    expect(result.direction).toBe("stable");
  });

  it("flags approaching-threshold when still capable but declining toward 1.33", () => {
    const windows = [
      window({ window_start: "2026-01-01T00:00:00Z", cpk: "1.60" }),
      window({ window_start: "2026-01-02T00:00:00Z", cpk: "1.50" }),
      window({ window_start: "2026-01-03T00:00:00Z", cpk: "1.40" }),
    ];

    const result = summarizeCapabilityTrend(windows);
    expect(result.direction).toBe("declining");
    expect(result.approachingThreshold).toBe(true);
    expect(result.text).toMatch(/approaching the 1\.33 capability threshold/);
  });

  it("does not flag approaching-threshold once already below the threshold", () => {
    // Already below 1.33 is an alarm concern (Fix 4), not a trend caption --
    // the text still reports the decline honestly but without the
    // "approaching" framing, to avoid duplicating alarm semantics.
    const windows = [
      window({ window_start: "2026-01-01T00:00:00Z", cpk: "1.20" }),
      window({ window_start: "2026-01-02T00:00:00Z", cpk: "1.00" }),
      window({ window_start: "2026-01-03T00:00:00Z", cpk: "0.80" }),
    ];

    const result = summarizeCapabilityTrend(windows);
    expect(result.direction).toBe("declining");
    expect(result.approachingThreshold).toBe(false);
  });

  it("only considers the last 3 windows with a defined Cpk", () => {
    const windows = [
      window({ window_start: "2026-01-01T00:00:00Z", cpk: "0.50" }), // would break "declining" if included
      window({ window_start: "2026-01-02T00:00:00Z", cpk: "1.80" }),
      window({ window_start: "2026-01-03T00:00:00Z", cpk: "1.50" }),
      window({ window_start: "2026-01-04T00:00:00Z", cpk: "1.20" }),
    ];

    const result = summarizeCapabilityTrend(windows);
    expect(result.direction).toBe("declining");
    expect(result.text).toContain("1.80 → 1.50 → 1.20");
  });

  it("skips null-cpk windows when picking the trailing windows to compare", () => {
    const windows = [
      window({ window_start: "2026-01-01T00:00:00Z", cpk: "1.80" }),
      window({ window_start: "2026-01-02T00:00:00Z", cpk: null }),
      window({ window_start: "2026-01-03T00:00:00Z", cpk: "1.40" }),
    ];

    const result = summarizeCapabilityTrend(windows);
    expect(result.direction).toBe("declining");
    expect(result.text).toContain("1.80 → 1.40");
  });
});
