import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

// LM.2 (docs/tasks/LM2-live-monitor-detail-view.md): jsdom has no
// ResizeObserver, but Recharts' <ResponsiveContainer> (used by TrendChart)
// requires one to mount at all -- stub it globally rather than per test file.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver;

// jsdom has no matchMedia either; ThemeProvider reads it for the "system"
// preference. Tests run as a light-themed OS.
window.matchMedia ??= ((query: string) => ({
  matches: false,
  media: query,
  onchange: null,
  addListener() {},
  removeListener() {},
  addEventListener() {},
  removeEventListener() {},
  dispatchEvent: () => false,
})) as typeof window.matchMedia;

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
  localStorage.removeItem("metro-intelligence.theme");
  localStorage.removeItem("metro-intelligence.demo.panes");
  document.documentElement.removeAttribute("data-theme");
});
afterAll(() => server.close());
