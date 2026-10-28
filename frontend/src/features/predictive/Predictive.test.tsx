import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { API_BASE_URL } from "../../lib/api";
import { renderAuthed } from "../../test/renderAuthed";
import { MODEL_LAB_FIXTURE } from "../../test/predictiveFixtures";
import { METROLOGIST_EMAIL, METROLOGIST_PASSWORD, server } from "../../test/server";
import { AiStep } from "../demo/steps/AiStep";

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

async function openTab(name: string) {
  renderAuthed(<AiStep />, CREDS);
  const tab = await screen.findByRole("tab", { name });
  await userEvent.click(tab);
}

describe("AiStep (IQ-F7)", () => {
  it("explains a missing module in Spanish and recovers with Reintentar", async () => {
    let calls = 0;
    server.use(
      http.get(`${API_BASE_URL}/predictive/model-lab`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({ detail: "Not Found" }, { status: 404 })
          : HttpResponse.json(MODEL_LAB_FIXTURE);
      }),
    );
    renderAuthed(<AiStep />, CREDS);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("No se pudo cargar este análisis.");
    expect(alert).toHaveTextContent(/reinicie el backend/);
    await userEvent.click(within(alert).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("El deep learning no superó al ML tabular")).toBeInTheDocument();
  });

  it("shows the precomputed study, its false-alarm cost and the computed DL vs ML conclusion", async () => {
    renderAuthed(<AiStep />, CREDS);
    expect(await screen.findByText(/Ejemplo ilustrativo \(cifras ficticias\)/)).toBeInTheDocument();
    expect(screen.getByText("El deep learning no superó al ML tabular")).toBeInTheDocument();
    expect(screen.getByText("Las falsas alarmas impiden el rechazo automático.")).toBeInTheDocument();
    const gb = screen.getByLabelText("Matriz de confusión Gradient Boosting");
    expect(within(gb).getByText("2,400")).toBeInTheDocument();
    expect(within(gb).getByText("48.0")).toBeInTheDocument();
    expect(screen.getAllByText(/Matriz aproximada/)).toHaveLength(1);
    // no curves or threshold the study did not produce
    expect(screen.getByText(/Sin curvas ROC\/PR ni umbral interactivo/)).toBeInTheDocument();
  });

  it("evaluates NOK waves per episode: detected, never anticipated, and re-runs with new rule parameters", async () => {
    await openTab("Oleadas NOK");
    const kpis = await screen.findByLabelText("Resultado por episodio");
    expect(within(kpis).getByText("0 de 2")).toBeInTheDocument();
    expect(within(kpis).getByText("2 de 2")).toBeInTheDocument();
    expect(screen.getByText("Detectar una racha iniciada no es predecir su inicio.")).toBeInTheDocument();
    expect(within(screen.getByLabelText("Episodios")).getAllByText("Detectada ya iniciada")).toHaveLength(2);
    expect(within(kpis).getByText("1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Ventana (grupos)"), { target: { value: "10" } });
    expect(await within(await screen.findByLabelText("Resultado por episodio")).findByText("4")).toBeInTheDocument();
  });

  it("runs CUSUM on a preset and labels an alarm without injected mechanism as a false positive", async () => {
    await openTab("CUSUM");
    expect(await screen.findByText("Cambio sostenido hacia arriba")).toBeInTheDocument();
    expect(screen.getByText(/Oleada inyectada el día 1.4/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Coplanaridad · INY-02" }));
    expect(await screen.findByText(/falso positivo del método/)).toBeInTheDocument();
  });

  it("labels the what-if as hypothetical and recomputes when the mold temperature moves", async () => {
    await openTab("What-if");
    expect(await screen.findByText("HIPOTÉTICO — mecanismo sintético.")).toBeInTheDocument();
    expect(await screen.findAllByText("0.6 ppm")).toHaveLength(2);
    fireEvent.change(screen.getByLabelText("Temperatura de molde"), { target: { value: "10" } });
    expect(await screen.findByText("43.00 %", {}, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.getByText(/El tiempo de ciclo no interviene/)).toBeInTheDocument();
  });

  it("compares the failure model with baselines on the same test period and follows the threshold", async () => {
    await openTab("Fallas de máquina");
    const kpis = await screen.findByLabelText("Métricas al umbral");
    expect(within(kpis).getByText("15 de 21")).toBeInTheDocument();
    const table = screen.getByLabelText("Comparación con líneas base");
    expect(within(table).getByText(/Alertar si hubo falla en la última hora/)).toBeInTheDocument();
    expect(within(table).getByText("0.399")).toBeInTheDocument();
    expect(screen.getByText("14 de 14")).toBeInTheDocument();
    expect(screen.getByText("1 de 7")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Umbral de alerta"), { target: { value: "0.7" } });
    expect(within(screen.getByLabelText("Métricas al umbral")).getByText("9 de 21")).toBeInTheDocument();
    expect(screen.getByText(/Requiere validación prospectiva/)).toBeInTheDocument();
  });
});
