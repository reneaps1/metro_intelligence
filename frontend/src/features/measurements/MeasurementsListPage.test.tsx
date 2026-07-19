import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { renderAuthed } from "../../test/renderAuthed";
import {
  server,
  VALID_EMAIL,
  VALID_PASSWORD,
  CHARACTERISTIC_FIXTURE,
  PART_FIXTURE,
  CLASSIFICATION_FIXTURE,
} from "../../test/server";
import { MeasurementsListPage } from "./MeasurementsListPage";

const API_BASE_URL = "http://localhost:8000/api/v1";

function renderPage() {
  return renderAuthed(<MeasurementsListPage />, { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/measurements" });
}

describe("MeasurementsListPage", () => {
  it("lists real characteristics with part, classification, spec, and a real-UUID trend link", async () => {
    renderPage();

    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
    expect(screen.getByText(PART_FIXTURE.code)).toBeInTheDocument();
    expect(screen.getByText(CLASSIFICATION_FIXTURE.name)).toBeInTheDocument();
    expect(screen.getByText(/10\.000 ±0\.050 mm/)).toBeInTheDocument();

    const link = screen.getByRole("link", { name: "View trend" });
    expect(link).toHaveAttribute("href", `/measurements/${CHARACTERISTIC_FIXTURE.id}`);
  });

  it("shows a loading state before the characteristics list resolves", async () => {
    let resolve: (value: { items: (typeof CHARACTERISTIC_FIXTURE)[]; total: number; page: number; page_size: number }) => void =
      () => {};
    const pending = new Promise<{ items: (typeof CHARACTERISTIC_FIXTURE)[]; total: number; page: number; page_size: number }>(
      (r) => {
        resolve = r;
      },
    );
    server.use(
      http.get(`${API_BASE_URL}/catalog/characteristics`, async () => {
        const body = await pending;
        return HttpResponse.json(body);
      }),
    );

    renderPage();

    expect(await screen.findByText("Loading…")).toBeInTheDocument();
    resolve({ items: [CHARACTERISTIC_FIXTURE], total: 1, page: 1, page_size: 200 });
    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
  });

  it("shows an empty-state message instead of an empty table when there are no characteristics", async () => {
    server.use(
      http.get(`${API_BASE_URL}/catalog/characteristics`, () =>
        HttpResponse.json({ items: [], total: 0, page: 1, page_size: 200 }),
      ),
    );

    renderPage();

    expect(await screen.findByText("No characteristics found.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows a clean error message when the characteristics request fails", async () => {
    server.use(
      http.get(`${API_BASE_URL}/catalog/characteristics`, () =>
        HttpResponse.json({ detail: "Internal error." }, { status: 500 }),
      ),
    );

    renderPage();

    expect(await screen.findByText("Something went wrong on our end. Please try again.")).toBeInTheDocument();
  });
});
