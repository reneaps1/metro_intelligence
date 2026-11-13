import { describe, expect, it } from "vitest";
import {
  INITIAL_EXPLORER_STATE,
  MAX_TRACES,
  clampWindow,
  explorerReducer,
  formatDuration,
  groupTracksByUnit,
  isStepSignal,
  panWindow,
  seriesStats,
  valueAt,
  zoomWindow,
} from "./explorer";
import { describeCorrelation, equation, formatCoefficient } from "./correlation";
import type { SignalInfo } from "./types";

function signal(key: string, unit: string, overrides: Partial<SignalInfo> = {}): SignalInfo {
  return {
    signal_id: `L1.INY-01.${key}`,
    key,
    machine_code: "INY-01",
    name: key,
    unit,
    value_type: "analog",
    sampling: "continuous",
    rate_hz: 1,
    informative: true,
    description: key,
    source_type: "SIMULATED",
    causal_imposed: false,
    ...overrides,
  };
}

const BOUNDS = { start: 0, end: 8 * 3_600_000 };

describe("explorerReducer", () => {
  it("adds signals once, assigns distinct colors and caps at MAX_TRACES", () => {
    let state = explorerReducer(INITIAL_EXPLORER_STATE, { type: "add", signal: signal("a", "°C") });
    state = explorerReducer(state, { type: "add", signal: signal("a", "°C") });
    expect(state.traces).toHaveLength(1);
    for (let i = 0; i < 20; i++) state = explorerReducer(state, { type: "add", signal: signal(`s${i}`, "bar") });
    expect(state.traces).toHaveLength(MAX_TRACES);
    expect(new Set(state.traces.map((t) => t.color)).size).toBe(MAX_TRACES);
  });

  it("toggles, moves and removes traces", () => {
    let state = explorerReducer(INITIAL_EXPLORER_STATE, {
      type: "addMany",
      signals: [signal("a", "°C"), signal("b", "bar"), signal("c", "mm")],
    });
    state = explorerReducer(state, { type: "toggle", signalId: "L1.INY-01.b" });
    expect(state.traces[1].visible).toBe(false);
    state = explorerReducer(state, { type: "move", signalId: "L1.INY-01.c", direction: -1 });
    expect(state.traces.map((t) => t.signal.key)).toEqual(["a", "c", "b"]);
    state = explorerReducer(state, { type: "move", signalId: "L1.INY-01.a", direction: -1 });
    expect(state.traces[0].signal.key).toBe("a");
    state = explorerReducer(state, { type: "remove", signalId: "L1.INY-01.a" });
    expect(state.traces.map((t) => t.signal.key)).toEqual(["c", "b"]);
  });

  it("sets cursors and resets everything", () => {
    let state = explorerReducer(INITIAL_EXPLORER_STATE, { type: "setCursor", cursor: "b", time: 42 });
    expect(state.cursors).toEqual({ a: null, b: 42 });
    state = explorerReducer(state, { type: "reset" });
    expect(state).toEqual(INITIAL_EXPLORER_STATE);
  });
});

describe("groupTracksByUnit", () => {
  it("never mixes units on one track and keeps first-appearance order", () => {
    const state = explorerReducer(INITIAL_EXPLORER_STATE, {
      type: "addMany",
      signals: [signal("t1", "°C"), signal("p", "bar"), signal("t2", "°C")],
    });
    const tracks = groupTracksByUnit(state.traces);
    expect(tracks.map((t) => t.unit)).toEqual(["°C", "bar"]);
    expect(tracks[0].traces.map((t) => t.signal.key)).toEqual(["t1", "t2"]);
  });
});

describe("valueAt", () => {
  const points: [number, number][] = [
    [0, 0],
    [10, 100],
    [20, 50],
  ];

  it("interpolates analog values and holds step values", () => {
    expect(valueAt(points, 5, false)).toBe(50);
    expect(valueAt(points, 15, false)).toBe(75);
    expect(valueAt(points, 15, true)).toBe(100);
    expect(valueAt(points, 20, false)).toBe(50);
  });

  it("returns null outside the data", () => {
    expect(valueAt(points, -1, false)).toBeNull();
    expect(valueAt(points, 21, false)).toBeNull();
    expect(valueAt([], 0, false)).toBeNull();
  });

  it("treats digital and per-cycle channels as step signals", () => {
    expect(isStepSignal(signal("alarm", "0/1", { value_type: "digital" }))).toBe(true);
    expect(isStepSignal(signal("hold", "bar", { sampling: "per_cycle" }))).toBe(true);
    expect(isStepSignal(signal("mold", "°C"))).toBe(false);
  });
});

describe("window math", () => {
  it("zooms around the center and clamps to bounds", () => {
    expect(zoomWindow({ start: 0, end: 3_600_000 }, 0.5, BOUNDS)).toEqual({ start: 900_000, end: 2_700_000 });
    expect(zoomWindow(BOUNDS, 2, BOUNDS)).toEqual(BOUNDS);
  });

  it("pans without leaving the scenario", () => {
    expect(panWindow({ start: 0, end: 1000_000 }, -0.5, BOUNDS)).toEqual({ start: 0, end: 1000_000 });
    expect(panWindow({ start: 0, end: 1000_000 }, 0.5, BOUNDS)).toEqual({ start: 500_000, end: 1_500_000 });
    const atEnd = panWindow({ start: BOUNDS.end - 1000, end: BOUNDS.end }, 1, BOUNDS);
    expect(atEnd.end).toBe(BOUNDS.end);
  });

  it("enforces a minimum span", () => {
    const w = clampWindow({ start: 5000, end: 5001 }, BOUNDS);
    expect(w.end - w.start).toBe(2000);
  });

  it("computes min/max and readable durations", () => {
    expect(seriesStats([[0, 3], [1, -2], [2, 7]])).toEqual({ min: -2, max: 7 });
    expect(seriesStats([])).toBeNull();
    expect(formatDuration(350)).toBe("350 ms");
    expect(formatDuration(12_400)).toBe("12.4 s");
    expect(formatDuration(-125_000)).toBe("2 min 05 s");
    expect(formatDuration(3_723_000)).toBe("1 h 02 min");
  });
});

describe("correlation wording", () => {
  it("describes strength and direction as association", () => {
    expect(describeCorrelation(null)).toMatch(/no definida/);
    expect(describeCorrelation(0.05)).toMatch(/sin asociación/i);
    expect(describeCorrelation(-0.2)).toBe("Asociación lineal negativa débil.");
    expect(describeCorrelation(0.45)).toBe("Asociación lineal positiva moderada.");
    expect(describeCorrelation(-0.91)).toBe("Asociación lineal negativa fuerte.");
  });

  it("formats coefficients and the regression equation", () => {
    expect(formatCoefficient(-0.000592)).toBe("-0.000592");
    expect(formatCoefficient(12.3712345)).toBe("12.37");
    expect(formatCoefficient(null)).toBe("—");
    expect(equation(-0.000592, 12.37)).toBe("y = 12.37 − 0.000592 · x");
    expect(equation(null, 1)).toBe("—");
  });
});
