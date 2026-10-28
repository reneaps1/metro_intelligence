import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderAuthed } from "../../test/renderAuthed";
import {
  METROLOGIST_EMAIL,
  METROLOGIST_PASSWORD,
  realQualityHandlers,
  server,
} from "../../test/server";
import { DemoSessionProvider } from "../../lib/demo/DemoSessionProvider";
import { DimensionalStep, QualityStep } from "../demo/steps/QualitySteps";

// IQ-F10/F11: steps 2-3 over the customer's REAL dataset (fictitious fixture).

const CREDS = { email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD };

beforeEach(() => {
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
    width: 800,
    height: 240,
    top: 0,
    left: 0,
    right: 800,
    bottom: 240,
    x: 0,
    y: 0,
    toJSON: () => {},
  });
});

function render(ui: React.ReactElement, seen: URLSearchParams[] = []) {
  server.use(...realQualityHandlers(seen));
  return renderAuthed(<DemoSessionProvider>{ui}</DemoSessionProvider>, CREDS);
}

describe("QualityStep with the REAL dataset", () => {
  it("prefers the REAL dataset and labels it as real", async () => {
    render(<QualityStep />);
    const kpis = await screen.findByLabelText("Indicadores de calidad");
    const picker = screen.getByRole("combobox", { name: "Dataset analizado" });
    expect(
      within(picker).getByRole("option", {
        name: "Real · Datos reales · Cliente demo",
      }),
    ).toBeInTheDocument();
    expect((picker as HTMLSelectElement).value).toBe("real-dimensional");
    expect(
      screen.getByText(/Período cerrado del cliente \(Cliente demo\)/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Horas en hora local de planta \(UTC−05:00\)/)).toBeInTheDocument();
    expect(
      within(kpis).queryByText("Grupos inspeccionados"),
    ).not.toBeInTheDocument();
    expect(within(kpis).getByText("Cav. 3")).toBeInTheDocument();
    expect(
      within(kpis).getByText("veredicto de la máquina"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Ninguna cota seleccionada tiene tolerancias/),
    ).not.toBeInTheDocument();
  });

  it("shows the station Pareto, mold cavities, the nest x station map and data quality", async () => {
    render(<QualityStep />);
    await screen.findByLabelText("Indicadores de calidad");
    expect(
      screen.getByText("Dónde falla · 1ª estación"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("NOK por cavidad de molde · IC 95 %"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Mapa de calor nido por estación" }),
    ).toBeInTheDocument();
    const quality = screen.getByLabelText("Calidad del dato");
    expect(
      within(quality).getByText("Piezas con valores repetidos"),
    ).toBeInTheDocument();
    expect(within(quality).getByText("12")).toBeInTheDocument();
  });

  it("sends station, mold cavity and suspect-data filters; clearing keeps the dataset", async () => {
    const user = userEvent.setup();
    const seen: URLSearchParams[] = [];
    render(<QualityStep />, seen);
    const kpis = await screen.findByLabelText("Indicadores de calidad");

    await user.click(
      screen.getByRole("button", { name: "Estación B por nido" }),
    );
    expect(await within(kpis).findByText("9")).toBeInTheDocument();
    expect(seen.at(-1)?.get("stations")).toBe("st_b");

    await user.click(
      screen.getByRole("button", { name: "Cavidad de molde 3" }),
    );
    await user.click(
      screen.getByRole("button", {
        name: /Excluir piezas con valores repetidos/,
      }),
    );
    expect(await within(kpis).findByText("888")).toBeInTheDocument();
    const last = seen.at(-1);
    expect(last?.get("mold_cavities")).toBe("3");
    expect(last?.get("exclude_flags")).toBe("2");

    await user.click(
      screen.getByRole("button", { name: /limpiar filtros \(3\)/i }),
    );
    expect(await within(kpis).findByText("900")).toBeInTheDocument();
    expect(
      (
        screen.getByRole("combobox", {
          name: "Dataset analizado",
        }) as HTMLSelectElement
      ).value,
    ).toBe("real-dimensional");
    expect(seen.at(-1)?.get("dataset")).toBe("real-dimensional");
  });

  it("keeps an explicit choice of the synthetic dataset", async () => {
    const user = userEvent.setup();
    render(<QualityStep />);
    await screen.findByLabelText("Indicadores de calidad");
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Dataset analizado" }),
      "demo-synthetic-dimensional",
    );
    expect(
      await screen.findByText(/Dataset dimensional sintético/, {
        selector: "strong",
      }),
    ).toBeInTheDocument();
    expect(
      (
        screen.getByRole("combobox", {
          name: "Dataset analizado",
        }) as HTMLSelectElement
      ).value,
    ).toBe("demo-synthetic-dimensional");
  });
});

describe("DimensionalStep with the REAL dataset", () => {
  it("offers grouping by mold cavity and explains the reported NOK markers", async () => {
    render(<DimensionalStep />);
    await screen.findByLabelText("Estadística de la cota");
    const options = within(
      screen.getByRole("combobox", { name: "Comparar por" }),
    ).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual([
      "Nido",
      "Cavidad de molde",
    ]);
  });
});
