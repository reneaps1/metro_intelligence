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
  CHARACTERISTIC_FIXTURE,
  SERIES_FIXTURE,
  CAPABILITY_HISTORY_FIXTURE,
} from "../../test/server";
import { LiveMonitorDetailPage } from "./LiveMonitorDetailPage";

const API_BASE_URL = "http://localhost:8000/api/v1";

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

  it("surfaces a clean error message when the series request fails", async () => {
    server.use(
      http.get(`${API_BASE_URL}/characteristics/:id/series`, () =>
        HttpResponse.json({ detail: "Characteristic not found." }, { status: 404 }),
      ),
    );

    renderPage();

    expect(await screen.findByText("Characteristic not found.")).toBeInTheDocument();
  });
});
