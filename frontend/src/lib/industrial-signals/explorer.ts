import type { SignalInfo } from "./types";

// IQ-F3: pure state and math for the iba-style signal explorer. Kept free of
// React/Recharts so cursor values, zoom and unit grouping are unit-tested.

export const MAX_TRACES = 8;
export const TRACE_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "#e879f9",
  "#22d3ee",
];
export const MIN_WINDOW_MS = 2_000;

export interface TimeWindow {
  start: number;
  end: number;
}

export interface Trace {
  signal: SignalInfo;
  color: string;
  visible: boolean;
}

export type CursorId = "a" | "b";
export type ExplorerLayout = "tracks" | "overlay";

export interface ExplorerState {
  traces: Trace[];
  /** null = whole scenario */
  window: TimeWindow | null;
  cursors: Record<CursorId, number | null>;
  activeCursor: CursorId;
  layout: ExplorerLayout;
}

export const INITIAL_EXPLORER_STATE: ExplorerState = {
  traces: [],
  window: null,
  cursors: { a: null, b: null },
  activeCursor: "a",
  layout: "tracks",
};

export type ExplorerAction =
  | { type: "add"; signal: SignalInfo }
  | { type: "addMany"; signals: SignalInfo[] }
  | { type: "remove"; signalId: string }
  | { type: "toggle"; signalId: string }
  | { type: "move"; signalId: string; direction: -1 | 1 }
  | { type: "setWindow"; window: TimeWindow | null }
  | { type: "setCursor"; cursor: CursorId; time: number | null }
  | { type: "setActiveCursor"; cursor: CursorId }
  | { type: "setLayout"; layout: ExplorerLayout }
  | { type: "reset" };

function addTrace(traces: Trace[], signal: SignalInfo): Trace[] {
  if (traces.length >= MAX_TRACES || traces.some((t) => t.signal.signal_id === signal.signal_id)) {
    return traces;
  }
  const used = new Set(traces.map((t) => t.color));
  const color = TRACE_COLORS.find((c) => !used.has(c)) ?? TRACE_COLORS[traces.length % TRACE_COLORS.length];
  return [...traces, { signal, color, visible: true }];
}

export function explorerReducer(state: ExplorerState, action: ExplorerAction): ExplorerState {
  switch (action.type) {
    case "add":
      return { ...state, traces: addTrace(state.traces, action.signal) };
    case "addMany":
      return { ...state, traces: action.signals.reduce(addTrace, state.traces) };
    case "remove":
      return { ...state, traces: state.traces.filter((t) => t.signal.signal_id !== action.signalId) };
    case "toggle":
      return {
        ...state,
        traces: state.traces.map((t) => (t.signal.signal_id === action.signalId ? { ...t, visible: !t.visible } : t)),
      };
    case "move": {
      const index = state.traces.findIndex((t) => t.signal.signal_id === action.signalId);
      const target = index + action.direction;
      if (index < 0 || target < 0 || target >= state.traces.length) return state;
      const traces = [...state.traces];
      [traces[index], traces[target]] = [traces[target], traces[index]];
      return { ...state, traces };
    }
    case "setWindow":
      return { ...state, window: action.window };
    case "setCursor":
      return { ...state, cursors: { ...state.cursors, [action.cursor]: action.time } };
    case "setActiveCursor":
      return { ...state, activeCursor: action.cursor };
    case "setLayout":
      return { ...state, layout: action.layout };
    case "reset":
      return INITIAL_EXPLORER_STATE;
  }
}

/** Step rendering for anything that is not a continuously sampled analog value. */
export function isStepSignal(signal: SignalInfo): boolean {
  return signal.value_type !== "analog" || signal.sampling === "per_cycle";
}

export interface Track {
  unit: string;
  traces: Trace[];
}

/** One track per unit, in order of first appearance -- units are never mixed on one axis. */
export function groupTracksByUnit(traces: Trace[]): Track[] {
  const tracks: Track[] = [];
  for (const trace of traces) {
    const track = tracks.find((t) => t.unit === trace.signal.unit);
    if (track) track.traces.push(trace);
    else tracks.push({ unit: trace.signal.unit, traces: [trace] });
  }
  return tracks;
}

/** Value at time t: previous sample for step signals, linear interpolation otherwise. */
export function valueAt(points: [number, number][], t: number, step: boolean): number | null {
  if (points.length === 0 || t < points[0][0] || t > points[points.length - 1][0]) return null;
  let lo = 0;
  let hi = points.length - 1;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (points[mid][0] <= t) lo = mid;
    else hi = mid - 1;
  }
  const [t0, v0] = points[lo];
  if (step || t0 === t || lo === points.length - 1) return v0;
  const [t1, v1] = points[lo + 1];
  return v0 + ((v1 - v0) * (t - t0)) / (t1 - t0);
}

export function seriesStats(points: [number, number][]): { min: number; max: number } | null {
  if (points.length === 0) return null;
  let min = Infinity;
  let max = -Infinity;
  for (const [, v] of points) {
    if (v < min) min = v;
    if (v > max) max = v;
  }
  return { min, max };
}

/** Keep a window inside the scenario bounds with a sensible minimum span. */
export function clampWindow(window: TimeWindow, bounds: TimeWindow): TimeWindow {
  const boundsSpan = bounds.end - bounds.start;
  const span = Math.min(Math.max(window.end - window.start, MIN_WINDOW_MS), boundsSpan);
  let start = Math.max(window.start, bounds.start);
  if (start + span > bounds.end) start = bounds.end - span;
  return { start, end: start + span };
}

/** factor < 1 zooms in, > 1 zooms out, around `center` (default: window middle). */
export function zoomWindow(window: TimeWindow, factor: number, bounds: TimeWindow, center?: number): TimeWindow {
  const mid = center ?? (window.start + window.end) / 2;
  const half = ((window.end - window.start) * factor) / 2;
  return clampWindow({ start: mid - half, end: mid + half }, bounds);
}

/** Shift by a fraction of the current span (negative = earlier). */
export function panWindow(window: TimeWindow, fraction: number, bounds: TimeWindow): TimeWindow {
  const delta = (window.end - window.start) * fraction;
  return clampWindow({ start: window.start + delta, end: window.end + delta }, bounds);
}

/** "T+hh:mm" (or "T+hh:mm:ss") relative to the scenario start. */
export function formatRelative(t: number, origin: number, withSeconds = false): string {
  const total = Math.max(0, Math.floor((t - origin) / 1000));
  const hh = String(Math.floor(total / 3600)).padStart(2, "0");
  const mm = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  return withSeconds ? `T+${hh}:${mm}:${ss}` : `T+${hh}:${mm}`;
}

export function formatDuration(ms: number): string {
  const abs = Math.abs(ms);
  if (abs < 1000) return `${Math.round(abs)} ms`;
  if (abs < 60_000) return `${(abs / 1000).toFixed(1)} s`;
  const totalSeconds = Math.round(abs / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return h > 0 ? `${h} h ${String(m).padStart(2, "0")} min` : `${m} min ${String(s).padStart(2, "0")} s`;
}

export function formatValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("es-MX", { maximumFractionDigits: Math.abs(value) >= 100 ? 1 : 4 });
}
