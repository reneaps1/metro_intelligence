import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { renderAuthed } from "../../test/renderAuthed";
import { VALID_EMAIL, VALID_PASSWORD, CHARACTERISTIC_FIXTURE, PART_FIXTURE } from "../../test/server";
import type { LiveMonitorEvent, LiveSocketConnectionState } from "../../lib/live-monitor/types";
import { LiveMonitorPage } from "./LiveMonitorPage";

// LM.1 (docs/tasks/LM1-live-monitor-mvp.md): MSW has no WebSocket support, so
// the socket layer is mocked at the `useLiveSocket` hook boundary instead of
// the transport (vi.mock calls are hoisted above these imports by vitest, so
// the page picks up the mock regardless of import order). Everything below
// it -- the REST catalog lookups that pick which characteristics to watch,
// event aggregation, and rendering -- still goes through the real code path
// against the MSW-mocked `/catalog` API.
let mockEvents: LiveMonitorEvent[] = [];
let mockConnectionState: LiveSocketConnectionState = "open";

vi.mock("../../lib/live-monitor/useLiveSocket", () => ({
  useLiveSocket: () => ({ events: mockEvents, connectionState: mockConnectionState }),
}));

function renderPage() {
  return renderAuthed(
    <Routes>
      <Route path="/live-monitor" element={<LiveMonitorPage />} />
    </Routes>,
    { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/live-monitor" },
  );
}

describe("LiveMonitorPage", () => {
  beforeEach(() => {
    mockEvents = [];
    mockConnectionState = "open";
  });

  it("renders a signal card for the resolved characteristic, nothing hardcoded", async () => {
    renderPage();

    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
    expect(screen.getByText(PART_FIXTURE.code)).toBeInTheDocument();
  });

  it("shows OK once a point event arrives for the resolved characteristic", async () => {
    mockEvents = [
      {
        type: "point",
        characteristic_id: CHARACTERISTIC_FIXTURE.id,
        value: "10.010",
        deviation: "0.010",
        is_ok: true,
        measured_at: "2026-01-01T00:00:00Z",
        rationale: "Within tolerance (+0.010 mm from nominal).",
        engine_name: "compliance_engine",
        engine_version: "v1",
      },
    ];

    renderPage();

    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    expect(await screen.findByText("OK")).toBeInTheDocument();
    expect(screen.getByText("10.010 mm")).toBeInTheDocument();
  });

  it("shows NOK for an out-of-tolerance point", async () => {
    mockEvents = [
      {
        type: "point",
        characteristic_id: CHARACTERISTIC_FIXTURE.id,
        value: "10.200",
        deviation: "0.200",
        is_ok: false,
        measured_at: "2026-01-01T00:00:00Z",
        rationale: "0.150 mm above the upper tolerance limit.",
        engine_name: "compliance_engine",
        engine_version: "v1",
      },
    ];

    renderPage();

    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    expect(await screen.findByText("NOK")).toBeInTheDocument();
  });

  it("surfaces the socket's reconnecting state", async () => {
    mockConnectionState = "reconnecting";
    renderPage();

    expect(await screen.findByText(/reconnecting/i)).toBeInTheDocument();
  });

  it("surfaces a denied connection distinctly from a dropped one (no silent infinite retry)", async () => {
    mockConnectionState = "denied";
    renderPage();

    expect(await screen.findByText(/access denied/i)).toBeInTheDocument();
    expect(screen.queryByText(/reconnecting/i)).not.toBeInTheDocument();
  });

  it("expands a signal's detail panel on click and collapses it again", async () => {
    const user = userEvent.setup();
    mockEvents = [
      {
        type: "point",
        characteristic_id: CHARACTERISTIC_FIXTURE.id,
        value: "9.990",
        deviation: "-0.010",
        is_ok: true,
        measured_at: "2026-01-01T00:00:00Z",
        rationale: "Within tolerance (-0.010 mm from nominal).",
        engine_name: "compliance_engine",
        engine_version: "v1",
      },
      {
        type: "point",
        characteristic_id: CHARACTERISTIC_FIXTURE.id,
        value: "10.010",
        deviation: "0.010",
        is_ok: true,
        measured_at: "2026-01-02T00:00:00Z",
        rationale: "Within tolerance (+0.010 mm from nominal).",
        engine_name: "compliance_engine",
        engine_version: "v1",
      },
    ];

    renderPage();
    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    expect(screen.queryByText(/view full detail/i)).not.toBeInTheDocument();

    await user.click(screen.getByText(CHARACTERISTIC_FIXTURE.name));

    expect(await screen.findByText("Within tolerance (+0.010 mm from nominal).")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view full detail/i })).toHaveAttribute(
      "href",
      `/measurements/${CHARACTERISTIC_FIXTURE.id}`,
    );

    await user.click(screen.getByRole("button", { name: /hide detail/i }));
    expect(screen.queryByText(/view full detail/i)).not.toBeInTheDocument();
  });
});
