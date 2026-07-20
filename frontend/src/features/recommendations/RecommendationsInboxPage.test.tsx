import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { renderAuthed } from "../../test/renderAuthed";
import { VALID_EMAIL, VALID_PASSWORD, METROLOGIST_EMAIL, METROLOGIST_PASSWORD } from "../../test/server";
import { CHARACTERISTICS, PARTS, RECOMMENDATIONS } from "../../lib/mock/fixtures";
import { RecommendationsInboxPage } from "./RecommendationsInboxPage";
import { CharacteristicTrendPage } from "../measurements/CharacteristicTrendPage";

// Two recommendations whose pattern is unique to a single characteristic
// (so their rationale/context text can't collide with any other card): the
// only "accepted" and only "pending-with-a-unique-name" fixtures available.
const PENDING_REC = RECOMMENDATIONS.find((r) => r.id === "rec-char-1001-1")!;
const ACCEPTED_REC = RECOMMENDATIONS.find((r) => r.id === "rec-char-1001-4")!;

function contextLabel(characteristicId: string): string {
  const characteristic = CHARACTERISTICS.find((c) => c.id === characteristicId)!;
  const part = PARTS.find((p) => p.id === characteristic.partId)!;
  return `${part.code} · ${characteristic.name}`;
}

const PENDING_CONTEXT = contextLabel(PENDING_REC.characteristicId);
const ACCEPTED_CONTEXT = contextLabel(ACCEPTED_REC.characteristicId);

// The context <p> sits two plain <div>s deep inside the Card's root div
// (header-inner div -> header-row div -> Card root) — climb to the root so
// the scoped queries below see the whole card (rationale, chip, buttons).
function cardFor(text: string) {
  const card = screen.getByText(text).closest("div")?.parentElement?.parentElement;
  if (!card) throw new Error(`Could not find card for "${text}"`);
  return within(card);
}

function renderPage(credentials: { email: string; password: string }) {
  return renderAuthed(
    <Routes>
      <Route path="/recommendations" element={<RecommendationsInboxPage />} />
      <Route path="/measurements/:characteristicId" element={<CharacteristicTrendPage />} />
    </Routes>,
    { ...credentials, route: "/recommendations" },
  );
}

describe("RecommendationsInboxPage", () => {
  it("lists recommendations with their state chip", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PENDING_CONTEXT);
    expect(cardFor(PENDING_CONTEXT).getByText("Pending")).toBeInTheDocument();
    expect(cardFor(ACCEPTED_CONTEXT).getByText("Accepted")).toBeInTheDocument();
  });

  it("shows accept/reject buttons for a quality_engineer (canDecide) role", async () => {
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PENDING_CONTEXT);
    const card = cardFor(PENDING_CONTEXT);
    expect(card.getByRole("button", { name: "Accept" })).toBeInTheDocument();
    expect(card.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("hides accept/reject buttons for a metrologist (read-only) role", async () => {
    renderPage({ email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD });

    await screen.findByText(PENDING_CONTEXT);
    const card = cardFor(PENDING_CONTEXT);
    expect(card.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(card.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    expect(card.getByText(/only quality engineer or admin roles/i)).toBeInTheDocument();
  });

  it("requires a non-empty comment before confirming a decision", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PENDING_CONTEXT);
    await user.click(cardFor(PENDING_CONTEXT).getByRole("button", { name: "Accept" }));

    const confirmButton = screen.getByRole("button", { name: /confirm accept/i });
    expect(confirmButton).toBeDisabled();

    await user.type(screen.getByLabelText(/reason \(required\)/i), "Matches the observed drift.");
    expect(confirmButton).toBeEnabled();
  });

  it("closes the modal and updates the state chip after a successful decision", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PENDING_CONTEXT);
    await user.click(cardFor(PENDING_CONTEXT).getByRole("button", { name: "Accept" }));
    await user.type(screen.getByLabelText(/reason \(required\)/i), "Matches the observed drift.");
    await user.click(screen.getByRole("button", { name: /confirm accept/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(cardFor(PENDING_CONTEXT).getByText("Accepted")).toBeInTheDocument();
  });

  it("filters by state", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PENDING_CONTEXT);
    await user.selectOptions(screen.getByLabelText(/filter by state/i), "accepted");

    expect(await screen.findByText(ACCEPTED_CONTEXT)).toBeInTheDocument();
    expect(screen.queryByText(PENDING_CONTEXT)).not.toBeInTheDocument();
  });

  it("expands to show evidence and navigates to a working characteristic trend page", async () => {
    const user = userEvent.setup();
    renderPage({ email: VALID_EMAIL, password: VALID_PASSWORD });

    await screen.findByText(PENDING_CONTEXT);
    await user.click(cardFor(PENDING_CONTEXT).getByRole("button", { name: /view evidence & history/i }));

    expect(await screen.findByText(/risk score/i)).toBeInTheDocument();
    const trendLink = screen.getByRole("link", { name: /view characteristic trend/i });
    expect(trendLink).toHaveAttribute("href", `/measurements/${PENDING_REC.characteristicId}`);

    await user.click(trendLink);

    expect(screen.queryByText(/characteristic not found/i)).not.toBeInTheDocument();
    expect(await screen.findByText(/cpk \(last 90d\)/i)).toBeInTheDocument();
  });
});
