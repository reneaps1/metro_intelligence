import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DemoBrand } from "./DemoBrand";

vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ user: { email: "viewer@demo.local" } }) }));

describe("DemoBrand", () => {
  it("marks the screen as an OnKaizen demo with the viewer watermark by default", () => {
    render(<DemoBrand />);
    expect(screen.getByTestId("demo-watermark")).toBeInTheDocument();
    expect(screen.getByText(/Propiedad de OnKaizen/)).toBeInTheDocument();
  });

  it("cannot be switched from the browser (no ?marca= override)", () => {
    window.history.pushState({}, "", "/?marca=off");
    render(<DemoBrand />);
    expect(screen.getByTestId("demo-watermark")).toBeInTheDocument();
    expect(screen.queryByRole("radiogroup")).not.toBeInTheDocument();
    window.history.pushState({}, "", "/");
  });
});
