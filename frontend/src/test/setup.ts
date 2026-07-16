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

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
});
afterAll(() => server.close());
