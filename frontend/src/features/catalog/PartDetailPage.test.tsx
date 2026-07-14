import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { renderAuthed } from "../../test/renderAuthed";
import { server } from "../../test/server";
import {
  VALID_EMAIL,
  VALID_PASSWORD,
  ADMIN_EMAIL,
  ADMIN_PASSWORD,
  PART_FIXTURE,
  CHARACTERISTIC_FIXTURE,
} from "../../test/server";
import { PartDetailPage } from "./PartDetailPage";

const API_BASE_URL = "http://localhost:8000/api/v1";

function renderPage(credentials: { email: string; password: string }) {
  return renderAuthed(
    <Routes>
      <Route path="/catalog/:partId" element={<PartDetailPage />} />
    </Routes>,
    { ...credentials, route: `/catalog/${PART_FIXTURE.id}` },
  );
}

describe("PartDetailPage", () => {
  it("shows the characteristic with its classification and active specification", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    expect(await screen.findByText(CHARACTERISTIC_FIXTURE.name)).toBeInTheDocument();
    expect(screen.getByText("Critical (CC)")).toBeInTheDocument();
    expect(screen.getByText("10.000 ±0.050 mm")).toBeInTheDocument();
  });

  it("hides 'Add characteristic' for a non-admin role", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    expect(screen.queryByRole("button", { name: /add characteristic/i })).not.toBeInTheDocument();
  });

  it("expands version history showing both the active and superseded specs, read-only for non-admin", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    await user.click(screen.getByRole("button", { name: /version history/i }));

    expect(await screen.findByText("Current")).toBeInTheDocument();
    expect(screen.getByText("Superseded")).toBeInTheDocument();
    expect(screen.getByText("10.000 ±0.100 mm")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create new version/i })).not.toBeInTheDocument();
  });

  it("lets admin create a new specification version with the correct payload", async () => {
    const user = userEvent.setup();
    let capturedBody: unknown = null;
    server.use(
      http.post(
        `${API_BASE_URL}/catalog/characteristics/${CHARACTERISTIC_FIXTURE.id}/specifications`,
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json(
            { ...CHARACTERISTIC_FIXTURE.active_specification, id: "new-version-id" },
            { status: 201 },
          );
        },
      ),
    );

    renderPage({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD });

    await screen.findByText(CHARACTERISTIC_FIXTURE.name);
    await user.click(screen.getByRole("button", { name: /version history/i }));
    await screen.findByRole("button", { name: /create new version/i });

    await user.type(screen.getByLabelText(/^nominal$/i), "10.500");
    await user.type(screen.getByLabelText(/lower tol\./i), "-0.040");
    await user.type(screen.getByLabelText(/upper tol\./i), "0.040");
    await user.click(screen.getByRole("button", { name: /create new version/i }));

    await waitFor(() => expect(capturedBody).not.toBeNull());
    expect(capturedBody).toMatchObject({ nominal: "10.500", lower_tol: "-0.040", upper_tol: "0.040", unit: "mm" });
  });
});
