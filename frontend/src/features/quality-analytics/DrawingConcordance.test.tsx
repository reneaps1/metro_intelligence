import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { DrawingConcordanceTable } from "./QualityOverview";

describe("DrawingConcordanceTable (IQ-F28)", () => {
  it("shows machine verdict vs drawing with shares and the not-measured count", () => {
    render(
      <DrawingConcordanceTable
        c={{
          machine_ok_drawing_ok: 90,
          machine_ok_drawing_out: 6,
          machine_nok_drawing_ok: 1,
          machine_nok_drawing_out: 3,
          not_measured: 4,
        }}
      />,
    );
    const table = screen.getByRole("table", { name: "Máquina vs plano" });
    const okRow = within(table).getByRole("row", { name: /^OK/ });
    expect(okRow).toHaveTextContent("90");
    expect(okRow).toHaveTextContent("6");
    expect(okRow).toHaveTextContent("6.00 %");
    expect(
      screen.getByText(/4 piezas sin esas características medidas/),
    ).toBeInTheDocument();
  });
});
