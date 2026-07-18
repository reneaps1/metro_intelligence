import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { renderAuthed } from "../../test/renderAuthed";
import {
  server,
  VALID_EMAIL,
  VALID_PASSWORD,
  AUDITOR_EMAIL,
  AUDITOR_PASSWORD,
  CHARACTERISTIC_FIXTURE,
  SERIES_FIXTURE,
  CAPABILITY_HISTORY_FIXTURE,
  ALERT_FIXTURE,
  SAMPLING_RECOMMENDATION_FIXTURE,
  REC_PENDING_FIXTURE,
} from "../../test/server";
import { LiveMonitorDetailPage, computeTrendControlLimits } from "./LiveMonitorDetailPage";
import type { CapabilityWindow } from "../../lib/live-monitor/types";

const API_BASE_URL = "http://localhost:8000/api/v1";

function capabilityWindow(overrides: Partial<CapabilityWindow> = {}): CapabilityWindow {
  return {
    window_start: "2026-01-01T00:00:00Z",
    window_end: "2026-01-10T00:00:00Z",
    point_count: 10,
    cpk: "1.50",
    center_line: "10.05",
    ucl: "10.15",
    lcl: "9.95",
    engine_name: "spc_engine",
    engine_version: "v1",
    nominal: "10.00",
    ...overrides,
  };
}

describe("computeTrendControlLimits", () => {
  it("returns null when there is no window", () => {
    expect(computeTrendControlLimits(null)).toBeNull();
  });

  it("returns null when the window has no nominal (e.g. fewer than 2 points)", () => {
    expect(computeTrendControlLimits(capabilityWindow({ nominal: null }))).toBeNull();
  });

  it("converts absolute center_line/ucl/lcl to deviation-space using the WINDOW's own nominal", () => {
    // Regression test for the code-review finding: a window can belong to an
    // older spec version than the characteristic's current active one. This
    // function only ever sees the window, so it can't accidentally reach for
    // some other, wrong nominal -- passing a nominal that differs from any
    // "current spec" is exactly what proves that.
    const window = capabilityWindow({ center_line: "12.05", ucl: "12.15", lcl: "11.95", nominal: "12.00" });

    const result = computeTrendControlLimits(window)!;
    expect(result.centerLine).toBeCloseTo(0.05, 6);
    expect(result.ucl).toBeCloseTo(0.15, 6);
    expect(result.lcl).toBeCloseTo(-0.05, 6);
  });

  it("uses a different window's different nominal correctly (not a hardcoded/shared value)", () => {
    const oldSpecWindow = capabilityWindow({ center_line: "10.05", ucl: "10.15", lcl: "9.95", nominal: "10.00" });
    const newSpecWindow = capabilityWindow({ center_line: "12.05", ucl: "12.15", lcl: "11.95", nominal: "12.00" });

    const oldResult = computeTrendControlLimits(oldSpecWindow)!;
    const newResult = computeTrendControlLimits(newSpecWindow)!;

    expect(oldResult.centerLine).toBeCloseTo(0.05, 6);
    expect(newResult.centerLine).toBeCloseTo(0.05, 6);
    // Same *relative* deviation despite very different absolute nominals --
    // proves each result used its own window's nominal, not one shared value.
  });
});

function renderPage() {
  return renderAuthed(
    <Routes>
      <Route path="/live-monitor/:characteristicId" element={<LiveMonitorDetailPage />} />
    </Routes>,
    { email: VALID_EMAIL, password: VALID_PASSWORD, route: `/live-monitor/${CHARACTERISTIC_FIXTURE.id}` },
  );
}

describe("LiveMonitorDetailPage", () => {
  it("renders the trend chart, control-limit stats, and Cpk history from real API data", async () => {
    renderPage();

    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
    // Cpk stat tile shows the real value from CAPABILITY_HISTORY_FIXTURE, not a placeholder.
    expect(await screen.findByText("1.80")).toBeInTheDocument();
    expect(screen.getByText("spc_engine v1")).toBeInTheDocument();
    expect(screen.getByText(`${SERIES_FIXTURE.total_points}`)).toBeInTheDocument();
  });

  it("shows a clean message instead of a chart when there aren't enough points", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/series`, () =>
        HttpResponse.json({ ...SERIES_FIXTURE, total_points: 1, returned_points: 1, points: SERIES_FIXTURE.points.slice(0, 1) }),
      ),
      http.get(`${API_BASE_URL}/characteristics/:id/capability-history`, () =>
        HttpResponse.json({ ...CAPABILITY_HISTORY_FIXTURE, windows: [] }),
      ),
    );

    renderPage();

    expect(await screen.findByText(/not enough points in this range to plot a trend/i)).toBeInTheDocument();
    expect(screen.getByText(/not enough points in this range to compute capability history/i)).toBeInTheDocument();
  });

  it("changing the date range re-fetches real data for the new range", async () => {
    const user = userEvent.setup();
    const requestedRanges: Array<{ from: string | null; to: string | null }> = [];
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/series`, ({ request }) => {
        const url = new URL(request.url);
        requestedRanges.push({ from: url.searchParams.get("from"), to: url.searchParams.get("to") });
        return HttpResponse.json(SERIES_FIXTURE);
      }),
    );

    renderPage();
    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    // Initial ("all") load has no from/to.
    await waitFor(() => expect(requestedRanges).toHaveLength(1));
    expect(requestedRanges[0]).toEqual({ from: null, to: null });

    await user.click(screen.getByRole("button", { name: "7d" }));

    await waitFor(() => expect(requestedRanges.length).toBeGreaterThan(1));
    const latest = requestedRanges[requestedRanges.length - 1];
    expect(latest.from).not.toBeNull();
    expect(latest.to).not.toBeNull();
  });

  it("shows no active-alarms card when there are no open alerts (the default fixture)", async () => {
    renderPage();

    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    expect(screen.queryByText(/active alarms/i)).not.toBeInTheDocument();
  });

  it("shows the active-alarms card with the real rationale and engine attribution for an open alert", async () => {
    server.use(
      http.get(`${API_BASE_URL}/alerts`, () =>
        HttpResponse.json({ items: [ALERT_FIXTURE], total: 1, page: 1, page_size: 50 }),
      ),
    );

    renderPage();

    expect(await screen.findByText(/active alarms/i)).toBeInTheDocument();
    expect(screen.getByText(ALERT_FIXTURE.rationale)).toBeInTheDocument();
    expect(screen.getByText(/alarm_rules_engine/)).toBeInTheDocument();
    expect(screen.getByText("Warning")).toBeInTheDocument();
  });

  it("acknowledges an alert and removes it from the list", async () => {
    const user = userEvent.setup();
    let acknowledged = false;
    server.use(
      http.get(`${API_BASE_URL}/alerts`, () =>
        HttpResponse.json({
          items: acknowledged ? [] : [ALERT_FIXTURE],
          total: acknowledged ? 0 : 1,
          page: 1,
          page_size: 50,
        }),
      ),
      http.post(`${API_BASE_URL}/alerts/:id/acknowledge`, () => {
        acknowledged = true;
        return HttpResponse.json({ ...ALERT_FIXTURE, acknowledged_at: "2026-01-06T00:00:00Z" });
      }),
    );

    renderPage();
    expect(await screen.findByText(/active alarms/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /acknowledge/i }));

    await waitFor(() => expect(screen.queryByText(/active alarms/i)).not.toBeInTheDocument());
  });

  it("shows a clean error and keeps the alert listed if acknowledging fails", async () => {
    const user = userEvent.setup();
    server.use(
      http.get(`${API_BASE_URL}/alerts`, () =>
        HttpResponse.json({ items: [ALERT_FIXTURE], total: 1, page: 1, page_size: 50 }),
      ),
      http.post(`${API_BASE_URL}/alerts/:id/acknowledge`, () =>
        HttpResponse.json({ detail: "Alert already acknowledged." }, { status: 409 }),
      ),
    );

    renderPage();
    expect(await screen.findByText(/active alarms/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /acknowledge/i }));

    expect(await screen.findByText("Alert already acknowledged.")).toBeInTheDocument();
    expect(screen.getByText(/active alarms/i)).toBeInTheDocument();
  });

  it("does not show the Acknowledge action for an auditor (read-only role)", async () => {
    server.use(
      http.get(`${API_BASE_URL}/alerts`, () =>
        HttpResponse.json({ items: [ALERT_FIXTURE], total: 1, page: 1, page_size: 50 }),
      ),
    );

    renderAuthed(
      <Routes>
        <Route path="/live-monitor/:characteristicId" element={<LiveMonitorDetailPage />} />
      </Routes>,
      { email: AUDITOR_EMAIL, password: AUDITOR_PASSWORD, route: `/live-monitor/${CHARACTERISTIC_FIXTURE.id}` },
    );

    expect(await screen.findByText(/active alarms/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /acknowledge/i })).not.toBeInTheDocument();
  });

  it("surfaces a clean error message when the series request fails", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/series`, () =>
        HttpResponse.json({ detail: "Characteristic not found." }, { status: 404 }),
      ),
    );

    renderPage();

    expect(await screen.findByText("Characteristic not found.")).toBeInTheDocument();
  });

  it("labels the Cpk-history trend as insufficient data with only one window (the default fixture)", async () => {
    renderPage();

    expect(await screen.findByText(/trend \(rule-based, from real cpk history\)/i)).toBeInTheDocument();
    expect(screen.getByText(/not enough cpk history yet/i)).toBeInTheDocument();
  });

  it("shows a rule-based declining trend from real Cpk history, never ML/prediction language", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/capability-history`, () =>
        HttpResponse.json({
          ...CAPABILITY_HISTORY_FIXTURE,
          windows: [
            { ...CAPABILITY_HISTORY_FIXTURE.windows[0], window_start: "2026-01-01T00:00:00Z", cpk: "1.80" },
            { ...CAPABILITY_HISTORY_FIXTURE.windows[0], window_start: "2026-01-02T00:00:00Z", cpk: "1.40" },
            { ...CAPABILITY_HISTORY_FIXTURE.windows[0], window_start: "2026-01-03T00:00:00Z", cpk: "1.10" },
          ],
        }),
      ),
    );

    renderPage();

    expect(await screen.findByText(/1\.80 → 1\.40 → 1\.10/)).toBeInTheDocument();
    expect(screen.queryByText(/predict/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bML\b/)).not.toBeInTheDocument();
  });

  // --- EXPERIMENTAL adaptive sampling (Thompson Sampling) -------------------

  it("shows the experimental adaptive sampling block with the recommended frequency and EXPERIMENTAL label", async () => {
    renderPage();

    expect(await screen.findByText(/muestreo adaptativo: cada 20 piezas/i)).toBeInTheDocument();
    expect(screen.getByText(/experimental — muestreo adaptativo/i)).toBeInTheDocument();
    expect(screen.getByText(/advisory only, does not replace the engineer's judgment/i)).toBeInTheDocument();
  });

  it("colors the recommended frequency using the ok/warning/nok status rule, always paired with the numeric text", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/sampling-recommendation`, () =>
        HttpResponse.json({ ...SAMPLING_RECOMMENDATION_FIXTURE, recommended_frequency: 50 }),
      ),
    );
    renderPage();

    const sparse = await screen.findByText(/muestreo adaptativo: cada 50 piezas/i);
    expect(sparse.className).toContain("text-status-ok");

    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/sampling-recommendation`, () =>
        HttpResponse.json({ ...SAMPLING_RECOMMENDATION_FIXTURE, recommended_frequency: 5 }),
      ),
    );
    renderPage();

    const tight = await screen.findAllByText(/muestreo adaptativo: cada 5 piezas/i);
    expect(tight[tight.length - 1].className).toContain("text-status-nok");
  });

  it("shows the existing rule-based recommendations list side by side with the adaptive sampling block", async () => {
    renderPage();

    expect(await screen.findByText(/muestreo adaptativo: cada 20 piezas/i)).toBeInTheDocument();
    expect(screen.getByText(/existing recommendations \(rule-based\)/i)).toBeInTheDocument();
    expect(screen.getByText(REC_PENDING_FIXTURE.rationale)).toBeInTheDocument();
  });

  it("shows a conflict warning when the adaptive result disagrees with an existing pending recommendation", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/sampling-recommendation`, () =>
        HttpResponse.json({
          ...SAMPLING_RECOMMENDATION_FIXTURE,
          conflicting_recommendations: [
            {
              id: REC_PENDING_FIXTURE.id,
              type: REC_PENDING_FIXTURE.recommendation_type,
              status: REC_PENDING_FIXTURE.state,
              title: "Frequency increase: Trend approaching upper tolerance.",
              reason: REC_PENDING_FIXTURE.rationale,
              conflict_reason: "Asks for tighter inspection; this proposes a routine frequency instead.",
            },
          ],
        }),
      ),
    );

    renderPage();

    expect(await screen.findByText(/conflicts with existing recommendation/i)).toBeInTheDocument();
    expect(screen.getByText(/asks for tighter inspection/i)).toBeInTheDocument();
  });

  it("shows a loading state for the adaptive sampling block independently of the Cpk history chart", async () => {
    let resolveSampling: (value: typeof SAMPLING_RECOMMENDATION_FIXTURE) => void = () => {};
    const pending = new Promise<typeof SAMPLING_RECOMMENDATION_FIXTURE>((resolve) => {
      resolveSampling = resolve;
    });
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/sampling-recommendation`, async () => {
        const body = await pending;
        return HttpResponse.json(body);
      }),
    );

    renderPage();

    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
    expect(await screen.findByText(/loading adaptive sampling recommendation/i)).toBeInTheDocument();

    resolveSampling(SAMPLING_RECOMMENDATION_FIXTURE);

    await waitFor(() => expect(screen.getByText(/muestreo adaptativo: cada 20 piezas/i)).toBeInTheDocument());
  });

  it("shows low-confidence, insufficient-history language when too few windows have been analyzed", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/sampling-recommendation`, () =>
        HttpResponse.json({
          ...SAMPLING_RECOMMENDATION_FIXTURE,
          recommended_frequency: 5,
          confidence: 0,
          windows_analyzed: 1,
        }),
      ),
    );

    renderPage();

    expect(await screen.findByText(/low confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/not a definitive result/i)).toBeInTheDocument();
  });

  it("never hides the existing recommendation system, even when the adaptive sampling request fails", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/sampling-recommendation`, () =>
        HttpResponse.json({ detail: "Internal error." }, { status: 500 }),
      ),
    );

    renderPage();

    expect(await screen.findByText(/existing recommendations \(rule-based\)/i)).toBeInTheDocument();
    expect(screen.getByText(REC_PENDING_FIXTURE.rationale)).toBeInTheDocument();
  });

  it("never embeds an accept/reject control in the adaptive sampling block, only a link to the recommendations inbox", async () => {
    renderPage();

    expect(await screen.findByText(/muestreo adaptativo: cada 20 piezas/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /accept/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view inbox/i })).toHaveAttribute("href", "/recommendations");
  });
});
