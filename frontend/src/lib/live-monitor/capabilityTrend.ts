import type { CapabilityWindow } from "./types";
import { CPK_CAPABLE_THRESHOLD } from "./constants";

// Live Monitor deep-dive fix (2026-07): "I don't see anything that helps
// anticipate problems." This project has an explicit, documented policy
// against simulating ML (CLAUDE.md §16/§22, docs/design/live-monitor-panel.md
// lines 16-22) -- rules-based engines are the baseline, never a fake model.
// So instead of a forecast, this is a plain comparison across the real,
// already-computed Cpk values from `capability-history` (the real SPC
// engine's per-window output) -- no forecasting, no invented confidence
// numbers, only direct comparisons on real decimals already fetched by the
// page.
const WINDOWS_CONSIDERED = 3;
// "Approaching" the threshold while still capable: within 15% of it. Not a
// standard SPC constant like 1.33 itself -- a deliberate, documented choice
// for when to soften the trend language from "declining" to "declining,
// approaching the threshold".
const APPROACHING_MARGIN = 0.15;

export type CapabilityTrendDirection = "declining" | "improving" | "stable" | "insufficient_data";

export interface CapabilityTrendSummary {
  direction: CapabilityTrendDirection;
  text: string;
  approachingThreshold: boolean;
}

function isStrictlyDecreasing(values: number[]): boolean {
  return values.every((value, index) => index === 0 || value < values[index - 1]);
}

function isStrictlyIncreasing(values: number[]): boolean {
  return values.every((value, index) => index === 0 || value > values[index - 1]);
}

export function summarizeCapabilityTrend(windows: CapabilityWindow[]): CapabilityTrendSummary {
  const chronological = [...windows].sort(
    (a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime(),
  );
  const withCpk = chronological.filter((w) => w.cpk !== null).slice(-WINDOWS_CONSIDERED);
  const values = withCpk.map((w) => Number(w.cpk));

  if (values.length < 2) {
    return {
      direction: "insufficient_data",
      text: "Not enough Cpk history yet to describe a trend (need at least 2 windows with a defined Cpk).",
      approachingThreshold: false,
    };
  }

  const last = values[values.length - 1];
  const sequence = values.map((v) => v.toFixed(2)).join(" → ");
  const approachingThreshold =
    last >= CPK_CAPABLE_THRESHOLD && last <= CPK_CAPABLE_THRESHOLD * (1 + APPROACHING_MARGIN);

  if (isStrictlyDecreasing(values)) {
    const suffix = approachingThreshold ? `, approaching the ${CPK_CAPABLE_THRESHOLD} capability threshold` : "";
    return {
      direction: "declining",
      text: `Cpk declining across the last ${values.length} windows: ${sequence}${suffix}.`,
      approachingThreshold,
    };
  }

  if (isStrictlyIncreasing(values)) {
    return {
      direction: "improving",
      text: `Cpk improving across the last ${values.length} windows: ${sequence}.`,
      approachingThreshold: false,
    };
  }

  return {
    direction: "stable",
    text: `Cpk stable across the last ${values.length} windows: ${sequence}.`,
    approachingThreshold: false,
  };
}
