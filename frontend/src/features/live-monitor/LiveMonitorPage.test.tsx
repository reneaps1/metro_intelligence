import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { renderAuthed } from "../../test/renderAuthed";
import {
  VALID_EMAIL,
  VALID_PASSWORD,
  METROLOGIST_EMAIL,
  METROLOGIST_PASSWORD,
  CHARACTERISTIC_FIXTURE,
  PART_FIXTURE,
  SCENARIO_CHARACTERISTIC_ID,
} from "../../test/server";
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
const mockSendControl = vi.fn();
// LM.3: capture the exact `characteristicIds` the page passes in, so scenario
// switching (which should feed a *different* id set into the socket) is
// verifiable without a real WebSocket.
const useLiveSocketSpy = vi.fn((_ids: string[]) => ({
  events: mockEvents,
  connectionState: mockConnectionState,
  sendControl: mockSendControl,
}));

vi.mock("../../lib/live-monitor/useLiveSocket", () => ({
  useLiveSocket: (ids: string[]) => useLiveSocketSpy(ids),
}));

function renderPage(credentials: { email: string; password: string } = { email: VALID_EMAIL, password: VALID_PASSWORD }) {
  return renderAuthed(
    <Routes>
      <Route path="/live-monitor" element={<LiveMonitorPage />} />
    </Routes>,
    { ...credentials, route: "/live-monitor" },
  );
}

describe("LiveMonitorPage", () => {
  beforeEach(() => {
    mockEvents = [];
    mockConnectionState = "open";
    mockSendControl.mockClear();
    useLiveSocketSpy.mockClear();
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

  // --- LM.3: presenter controls ---------------------------------------------

  it("shows presenter controls for a quality_engineer (has live_monitor.update)", async () => {
    renderPage();
    await screen.findByText(CHARACTERISTIC_FIXTURE.name);

    expect(screen.getByRole("button", { name: /pause/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/playback speed/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/scenario/i)).toBeInTheDocument();
  });

  it("hides presenter controls for a metrologist (view-only, no live_monitor.update)", async () => {
    renderPage({ email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD });
    await screen.findByText(CHARACTERISTIC_FIXTURE.name);

    expect(screen.queryByRole("button", { name: /pause/i })).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/playback speed/i)).not.toBeInTheDocument();
  });

  it("sends a pause control message and flips the button to Play", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(CHARACTERISTIC_FIXTURE.name);

    await user.click(screen.getByRole("button", { name: /pause/i }));

    expect(mockSendControl).toHaveBeenCalledWith({ type: "control", action: "pause" });
    expect(await screen.findByRole("button", { name: /play/i })).toBeInTheDocument();
  });

  it("sends a set_speed control message when the speed selector changes", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(CHARACTERISTIC_FIXTURE.name);

    await user.selectOptions(screen.getByLabelText(/playback speed/i), "20");

    expect(mockSendControl).toHaveBeenCalledWith({
      type: "control",
      action: "set_speed",
      speed_multiplier: 20,
    });
  });

  it("switches the watched characteristics when a scenario is selected, and back on 'Default mix'", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    expect(useLiveSocketSpy).toHaveBeenLastCalledWith([CHARACTERISTIC_FIXTURE.id]);

    await user.selectOptions(screen.getByLabelText(/scenario/i), "high_variance");

    await waitFor(() => {
      expect(useLiveSocketSpy).toHaveBeenLastCalledWith([SCENARIO_CHARACTERISTIC_ID]);
    });

    await user.selectOptions(screen.getByLabelText(/scenario/i), "Default mix");

    await waitFor(() => {
      expect(useLiveSocketSpy).toHaveBeenLastCalledWith([CHARACTERISTIC_FIXTURE.id]);
    });
  });
});
