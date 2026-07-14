import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { renderAuthed } from "../../test/renderAuthed";
import { VALID_EMAIL, VALID_PASSWORD, ADMIN_EMAIL, ADMIN_PASSWORD, PART_FIXTURE } from "../../test/server";
import { CatalogListPage } from "./CatalogListPage";

function renderPage(credentials: { email: string; password: string }) {
  return renderAuthed(
    <Routes>
      <Route path="/catalog" element={<CatalogListPage />} />
    </Routes>,
    { ...credentials, route: "/catalog" },
  );
}

describe("CatalogListPage", () => {
  it("lists parts from the real API with their product family", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    expect(await screen.findByText(PART_FIXTURE.name)).toBeInTheDocument();
    expect(screen.getByText(PART_FIXTURE.code)).toBeInTheDocument();
    expect(screen.getByText("Bracket Family (Demo)", { selector: "p" })).toBeInTheDocument();
  });

  it("hides the create button for a non-admin role", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PART_FIXTURE.name);
    expect(screen.queryByRole("button", { name: /new part number/i })).not.toBeInTheDocument();
  });

  it("shows the create button and form for admin", async () => {
    const user = userEvent.setup();
    renderPage({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD });

    await screen.findByText(PART_FIXTURE.name);
    await user.click(screen.getByRole("button", { name: /new part number/i }));

    expect(screen.getByText("New part number")).toBeInTheDocument();
    expect(screen.getByLabelText("Product family")).toBeInTheDocument();
  });

  it("filters the visible list by search text", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PART_FIXTURE.name);
    await user.type(screen.getByLabelText(/search parts/i), "no-such-part");

    expect(await screen.findByText(/no parts match your search/i)).toBeInTheDocument();
    expect(screen.queryByText(PART_FIXTURE.name)).not.toBeInTheDocument();
  });
});
