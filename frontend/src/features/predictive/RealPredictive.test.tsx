import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { API_BASE_URL } from "../../lib/api";
import { renderAuthed } from "../../test/renderAuthed";
import { MODEL_LAB_STUDIES_FIXTURE, realPredictiveHandlers } from "../../test/predictiveFixtures";
import { METROLOGIST_EMAIL, METROLOGIST_PASSWORD, realQualityHandlers, server } from "../../test/server";
import { AiStep } from "../demo/steps/AiStep";

// IQ-F12: step 6 over the customer's REAL dataset (fictitious fixtures).

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

function render() {
  server.use(...realQualityHandlers(), ...realPredictiveHandlers);
  renderAuthed(<AiStep />, CREDS);
}

describe("AiStep with the REAL dataset", () => {
  it("defaults to real data and offers the REAL-only studies", async () => {
    render();
    const data = await screen.findByRole("group", { name: "Datos del laboratorio" });
    expect(within(data).getByRole("button", { name: /Reales · Cliente demo/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("tab", { name: "Alarma por cavidad" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Riesgo por pieza" })).toBeInTheDocument();
  });

  it("evaluates the cavity alarm retrospectively", async () => {
    const user = userEvent.setup();
    render();
    await user.click(await screen.findByRole("tab", { name: "Alarma por cavidad" }));
    const result = await screen.findByLabelText("Resultado de la alarma");
    expect(within(result).getByText("92.0 %")).toBeInTheDocument();
    expect(within(result).getByText("2 de 2")).toBeInTheDocument();
    expect(screen.getByText(/Una alarma no evita scrap por sí sola/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Alarma por grupo" })).toHaveTextContent("C3");
  });

  it("says when the per-piece model does not beat a simple rule", async () => {
    const user = userEvent.setup();
    render();
    await user.click(await screen.findByRole("tab", { name: "Riesgo por pieza" }));
    expect(await screen.findByText("El modelo no supera a una regla simple.")).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Modelo frente a líneas base" });
    expect(within(table).getByText("Línea base: tasa reciente de la cavidad")).toBeInTheDocument();
  });

  it("runs the waves on pieces with a NOK target and retrospective episodes", async () => {
    const user = userEvent.setup();
    render();
    await user.click(await screen.findByRole("tab", { name: "Oleadas NOK" }));
    const result = await screen.findByLabelText("Resultado por episodio");
    expect(within(result).getByText("Episodios")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "NOK que cuenta" })).toHaveValue("total");
    expect(screen.getByText(/episodio etiquetado a posteriori/)).toBeInTheDocument();
  });

  it("switches back to synthetic data and hides the REAL-only studies", async () => {
    const user = userEvent.setup();
    render();
    await user.click(await screen.findByRole("button", { name: "Sintéticos (demo)" }));
    expect(screen.queryByRole("tab", { name: "Alarma por cavidad" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sintéticos (demo)" })).toHaveAttribute("aria-pressed", "true");
  });

  it("lets the model lab switch between private studies", async () => {
    const user = userEvent.setup();
    server.use(http.get(`${API_BASE_URL}/predictive/model-lab`, () => HttpResponse.json(MODEL_LAB_STUDIES_FIXTURE)));
    render();
    const selector = await screen.findByRole("combobox", { name: "Estudio" });
    await user.selectOptions(selector, "1");
    expect(selector).toHaveDisplayValue("Segundo estudio ficticio");
  });
});
