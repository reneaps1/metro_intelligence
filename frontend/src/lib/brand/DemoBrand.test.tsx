import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DemoBrand } from "./DemoBrand";
import { BRAND_STORAGE_KEY } from "./brand";

vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: { email: "viewer@demo.local" } }) }));

afterEach(() => window.localStorage.removeItem(BRAND_STORAGE_KEY));

describe("DemoBrand", () => {
  it("marks the screen as an OnKaizen demo by default (watermark)", () => {
    render(<DemoBrand />);
    expect(screen.getByTestId("demo-watermark")).toBeInTheDocument();
    expect(screen.getByText(/Propiedad de OnKaizen/)).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
  });

  it("shows the proposal switcher only while previewing", () => {
    window.localStorage.setItem(BRAND_STORAGE_KEY, "c");
    render(<DemoBrand />);
    expect(screen.getByRole("radiogroup", { name: /Propuesta/ })).toBeInTheDocument();
    expect(screen.getByText("VERSIÓN DEMO")).toBeInTheDocument();
  });
});
