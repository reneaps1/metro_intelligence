import { describe, expect, it } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { renderAuthed } from "../../test/renderAuthed";
import {
  VALID_EMAIL,
  VALID_PASSWORD,
  METROLOGIST_EMAIL,
  METROLOGIST_PASSWORD,
  REC_PENDING_FIXTURE,
  REC_ACCEPTED_FIXTURE,
} from "../../test/server";
import { RecommendationsInboxPage } from "./RecommendationsInboxPage";

function renderPage(credentials: { email: string; password: string }) {
  return renderAuthed(
    <Routes>
      <Route path="/recommendations" element={<RecommendationsInboxPage />} />
    </Routes>,
    { ...credentials, route: "/recommendations" },
  );
}

describe("RecommendationsInboxPage", () => {
  it("lists recommendations with their state chip", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    expect(await screen.findByText(/increase inspection frequency/i)).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("Accepted")).toBeInTheDocument();
  });

  it("shows accept/reject buttons for a quality_engineer (canDecide) role", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(REC_PENDING_FIXTURE.rationale);
    expect(screen.getAllByRole("button", { name: "Accept" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Reject" })).toHaveLength(1);
  });

  it("hides accept/reject buttons for a metrologist (read-only) role", async () => {
    renderPage({ email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD });

    await screen.findByText(REC_PENDING_FIXTURE.rationale);
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    expect(screen.getByText(/only quality engineer or admin roles/i)).toBeInTheDocument();
  });

  it("requires a non-empty comment before confirming a decision", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(REC_PENDING_FIXTURE.rationale);
    await user.click(screen.getByRole("button", { name: "Accept" }));

    const confirmButton = screen.getByRole("button", { name: /confirm accept/i });
    expect(confirmButton).toBeDisabled();

    await user.type(screen.getByLabelText(/reason \(required\)/i), "Matches the observed drift.");
    expect(confirmButton).toBeEnabled();
  });

  it("closes the modal after a successful decision", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(REC_PENDING_FIXTURE.rationale);
    await user.click(screen.getByRole("button", { name: "Accept" }));
    await user.type(screen.getByLabelText(/reason \(required\)/i), "Matches the observed drift.");
    await user.click(screen.getByRole("button", { name: /confirm accept/i }));

    await screen.findByText(REC_PENDING_FIXTURE.rationale);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("filters by state", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(REC_PENDING_FIXTURE.rationale);
    await user.selectOptions(screen.getByLabelText(/filter by state/i), "accepted");

    expect(await screen.findByText(REC_ACCEPTED_FIXTURE.rationale)).toBeInTheDocument();
    expect(screen.queryByText(REC_PENDING_FIXTURE.rationale)).not.toBeInTheDocument();
  });

  it("expands to show evidence and links to the characteristic trend", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(REC_PENDING_FIXTURE.rationale);
    await user.click(screen.getAllByRole("button", { name: /view evidence & history/i })[0]);

    expect(await screen.findByText(/risk score 62/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view characteristic trend/i })).toHaveAttribute(
      "href",
      `/live-monitor/${REC_PENDING_FIXTURE.characteristic_id}`,
    );
  });
});
