import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderAuthed } from "../../test/renderAuthed";
import { METROLOGIST_EMAIL, METROLOGIST_PASSWORD } from "../../test/server";
import { DemoSessionProvider } from "../../lib/demo/DemoSessionProvider";
import { DimensionalStep, QualityStep } from "../demo/steps/QualitySteps";

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

function render(ui: React.ReactElement) {
  return renderAuthed(<DemoSessionProvider>{ui}</DemoSessionProvider>, CREDS);
}

describe("QualityStep (diagnosis)", () => {
  it("shows KPIs with denominators and the critical nest", async () => {
    render(<QualityStep />);
    const kpis = await screen.findByLabelText("Indicadores de calidad");
    expect(within(kpis).getByText("1,200")).toBeInTheDocument();
    expect(within(kpis).getByText("3.08 %")).toBeInTheDocument();
    expect(within(kpis).getByText("Nido 4")).toBeInTheDocument();
    expect(within(kpis).getByText(/RR 9.3× vs. resto/)).toBeInTheDocument();
    expect(screen.getByText(/Dataset dimensional sintético/, { selector: "strong" })).toBeInTheDocument();
  });

  it("filters actually change the data", async () => {
    const user = userEvent.setup();
    render(<QualityStep />);
    const kpis = await screen.findByLabelText("Indicadores de calidad");
    await user.click(screen.getByRole("button", { name: "Nido 4" }));
    expect(await within(kpis).findByText("300")).toBeInTheDocument();
    expect(within(kpis).getByText("9.33 %")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /limpiar filtros \(1\)/i })).toBeInTheDocument();
  });

  it("disables filters the dataset cannot support", async () => {
    render(<QualityStep />);
    await screen.findByLabelText("Indicadores de calidad");
    expect(screen.getByText(/no disponible en este dataset/)).toBeInTheDocument();
  });

  it("labels the report block as precomputed and illustrative", async () => {
    render(<QualityStep />);
    expect(await screen.findByText("Ejemplo ilustrativo (cifras ficticias)")).toBeInTheDocument();
    expect(screen.getByText("Precalculado")).toBeInTheDocument();
  });

  it("reveals the synthetic ground truth on demand", async () => {
    const user = userEvent.setup();
    render(<QualityStep />);
    await user.click(await screen.findByRole("button", { name: /verdad conocida/i }));
    expect(screen.getByText("Nido 4: longitud de pines desplazada.")).toBeInTheDocument();
  });
});

describe("DimensionalStep (exploration)", () => {
  it("shows capability and separates specification from control limits", async () => {
    render(<DimensionalStep />);
    const stats = await screen.findByLabelText("Estadística de la cota");
    expect(within(stats).getByText("1.19")).toBeInTheDocument();
    expect(within(stats).getByText("1.14")).toBeInTheDocument();
    expect(screen.getByText(/límites de especificación \(cliente\)/i)).toBeInTheDocument();
    expect(screen.getByText(/límites de control calculados del proceso/i)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /diagrama de caja/i })).toBeInTheDocument();
  });

  it("explains why Cp is missing for a unilateral tolerance", async () => {
    const user = userEvent.setup();
    render(<DimensionalStep />);
    await screen.findByLabelText("Estadística de la cota");
    await user.selectOptions(screen.getByRole("combobox", { name: "Cota a explorar" }), "Coplanarity");
    expect(await screen.findAllByText(/Cp no aplica a tolerancia unilateral/)).not.toHaveLength(0);
  });

  it("plots the pin X/Y position against its tolerance and marks the worst nest (IQ-F19)", async () => {
    const user = userEvent.setup();
    render(<DimensionalStep />);
    const kpis = await screen.findByLabelText("Indicadores de posición");
    expect(within(kpis).getByText("Fuera de Posición Ø0.08")).toBeInTheDocument();
    expect(within(kpis).getByText("1.0 %")).toBeInTheDocument();
    expect(within(kpis).getByText("+0.002 / +0.001")).toBeInTheDocument();
    const chart = screen.getByRole("img", { name: /Dispersión X\/Y de Posición de pin/ });
    expect(within(chart).getByText("POSICIÓN Ø0.08")).toBeInTheDocument();
    // Only the NOK piece takes the NOK accent (triangle); OK pieces are neutral dots.
    expect(chart.querySelectorAll("polygon")).toHaveLength(1);

    await user.click(within(screen.getByRole("group", { name: "Marcar por" })).getByRole("button", { name: "Nido" }));
    expect(await screen.findAllByTestId("xy-group")).toHaveLength(4);
    expect(screen.getByText(/resaltado, N4, la mayor tasa NOK/)).toBeInTheDocument();
    // Without mold cavities in the dataset there is no "Cavidad" option.
    expect(within(screen.getByRole("group", { name: "Marcar por" })).queryByRole("button", { name: "Cavidad" })).toBeNull();
  });

  it("does not offer grouping by a missing dimension", async () => {
    render(<DimensionalStep />);
    await screen.findByLabelText("Estadística de la cota");
    const options = within(screen.getByRole("combobox", { name: "Comparar por" })).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual(["Nido", "Máquina", "Turno"]);
  });
});
