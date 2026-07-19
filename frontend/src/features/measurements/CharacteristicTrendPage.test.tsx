import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { Routes, Route } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { renderAuthed } from "../../test/renderAuthed";
import {
  server,
  VALID_EMAIL,
  VALID_PASSWORD,
  CHARACTERISTIC_FIXTURE,
  PART_FIXTURE,
  CLASSIFICATION_FIXTURE,
  SERIES_FIXTURE,
} from "../../test/server";
import { CharacteristicTrendPage } from "./CharacteristicTrendPage";

const API_BASE_URL = "http://localhost:8000/api/v1";

function renderPage(characteristicId: string) {
  return renderAuthed(
    <Routes>
      <Route path="/measurements/:characteristicId" element={<CharacteristicTrendPage />} />
    </Routes>,
    { email: VALID_EMAIL, password: VALID_PASSWORD, route: `/measurements/${characteristicId}` },
  );
}

describe("CharacteristicTrendPage", () => {
  it("renders real characteristic, part, classification, spec, and stats from the real API", async () => {
    renderPage(CHARACTERISTIC_FIXTURE.id);

    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
    expect(await screen.findByText(new RegExp(PART_FIXTURE.code))).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Balloon #${CHARACTERISTIC_FIXTURE.balloon_number}`))).toBeInTheDocument();
    expect(screen.getAllByText(CLASSIFICATION_FIXTURE.name).length).toBeGreaterThan(0);
    expect(screen.getByText(/10\.000 ±0\.050 mm/)).toBeInTheDocument();
    // Cpk stat tile shows the real value from CAPABILITY_HISTORY_FIXTURE, not a placeholder.
    expect(await screen.findByText("1.80")).toBeInTheDocument();
    expect(screen.getByText(`${SERIES_FIXTURE.total_points}`)).toBeInTheDocument();
  });

  it("shows the exact backend 404 message for an unknown characteristic id (regression test)", async () => {
    // Regression test for the reported bug: a real UUID that legitimately
    // doesn't exist must show the real backend's 404 detail, not a stale
    // mock-fixture lookup mismatch for a UUID that actually does exist.
    renderPage("00000000-0000-0000-0000-000000000000");

    expect(await screen.findByText("Characteristic not found.")).toBeInTheDocument();
  });

  it("shows a loading state before the characteristic resolves", async () => {
    let resolve: (value: typeof CHARACTERISTIC_FIXTURE) => void = () => {};
    const pending = new Promise<typeof CHARACTERISTIC_FIXTURE>((r) => {
      resolve = r;
    });
    server.use(
      http.get(`${API_BASE_URL}/catalog/characteristics/:id`, async () => {
        const body = await pending;
        return HttpResponse.json(body);
      }),
    );

    renderPage(CHARACTERISTIC_FIXTURE.id);

    expect(await screen.findByText("Loading…")).toBeInTheDocument();
    resolve(CHARACTERISTIC_FIXTURE);
    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
  });

  it("shows a clean error message when the characteristic request fails with a server error", async () => {
    server.use(
      http.get(`${API_BASE_URL}/catalog/characteristics/:id`, () =>
        HttpResponse.json({ detail: "Internal error." }, { status: 500 }),
      ),
    );

    renderPage(CHARACTERISTIC_FIXTURE.id);

    expect(await screen.findByText("Something went wrong on our end. Please try again.")).toBeInTheDocument();
  });
});
