import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { API_BASE_URL } from "../../lib/api";
import { DemoSessionProvider } from "../../lib/demo/DemoSessionProvider";
import { renderAuthed } from "../../test/renderAuthed";
import { METROLOGIST_EMAIL, METROLOGIST_PASSWORD, server } from "../../test/server";
import { Route, Routes } from "react-router-dom";
import { DemoStepPage } from "../demo/DemoStepPage";
import { DimensionalImport } from "./DimensionalImport";

const CREDS = { email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD };
const csv = () => new File(["Fecha;Valor\n01/09/2026;1,0\n"], "ensayo.csv", { type: "text/csv" });

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

describe("DimensionalImport", () => {
  it("previews, shows the suggested mapping and reports quarantine and sampling", async () => {
    const user = userEvent.setup();
    const onImported = vi.fn();
    renderAuthed(<DimensionalImport onImported={onImported} />, CREDS);

    await user.upload(await screen.findByTestId("dimensional-file-input"), csv());
    expect(await screen.findByText("ensayo.csv")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Nido / cavidad" })).toHaveValue("Nido");
    expect(screen.getByRole("combobox", { name: "Valor medido" })).toHaveValue("Valor");
    expect(screen.getByRole("button", { name: /Largo/ })).toHaveAttribute("aria-pressed", "true");
    const previewTable = screen.getByRole("table", { name: "Vista previa del archivo" });
    expect(within(previewTable).getByText("P00001")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Validar y analizar" }));
    const result = await screen.findByLabelText("Resultado de la importación");
    expect(within(result).getByText("5,756")).toBeInTheDocument();
    expect(within(result).getByText(/Muestra de 5,761 filas \(~13 % del archivo\)/)).toBeInTheDocument();
    expect(within(result).getByText("Valor no numérico")).toBeInTheDocument();
    expect(within(result).getByText(/se interpretaron como UTC/)).toBeInTheDocument();

    await user.click(within(result).getByRole("button", { name: "Ver analíticas de este archivo" }));
    expect(onImported).toHaveBeenCalledWith(expect.objectContaining({ id: "import-0f0f", source_type: "IMPORTED" }));
  });

  it("blocks analysis while the mapping is incomplete", async () => {
    const user = userEvent.setup();
    renderAuthed(<DimensionalImport onImported={vi.fn()} />, CREDS);
    await user.upload(await screen.findByTestId("dimensional-file-input"), csv());
    await user.selectOptions(await screen.findByRole("combobox", { name: "Valor medido" }), "");
    expect(screen.getByText("Asigna la columna «Valor medido».")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validar y analizar" })).toBeDisabled();
  });

  it("shows backend errors and keeps the demo untouched", async () => {
    server.use(
      http.post(`${API_BASE_URL}/quality-analytics/imports/preview`, () =>
        HttpResponse.json({ detail: "File content does not look like a valid CSV file." }, { status: 422 }),
      ),
    );
    const user = userEvent.setup();
    renderAuthed(<DimensionalImport onImported={vi.fn()} />, CREDS);
    await user.upload(await screen.findByTestId("dimensional-file-input"), csv());
    expect(await screen.findByRole("alert")).toHaveTextContent("does not look like a valid CSV");
  });
});

describe("QualityStep with an imported CSV", () => {
  it("switches every analytic to the imported dataset and labels the source verdict apart", async () => {
    const user = userEvent.setup();
    renderAuthed(
      <DemoSessionProvider>
        <Routes>
          <Route path="/demo/:stepId" element={<DemoStepPage />} />
        </Routes>
      </DemoSessionProvider>,
      { ...CREDS, route: "/demo/quality" },
    );
    // DemoStepPage lazy-loads step 2 (IQ-F8).
    const kpis = await screen.findByLabelText("Indicadores de calidad", {}, { timeout: 5000 });
    expect(within(kpis).getByText("Nido 4")).toBeInTheDocument();
    expect(screen.getByText("Ejemplo ilustrativo (cifras ficticias)")).toBeInTheDocument();
    expect(screen.getByText("Simulado")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Importar CSV propio" }));
    await user.upload(await screen.findByTestId("dimensional-file-input"), csv());
    await user.click(await screen.findByRole("button", { name: "Validar y analizar" }));
    await user.click(await screen.findByRole("button", { name: "Ver analíticas de este archivo" }));

    const imported = await screen.findByText("Nido 11");
    expect(within(screen.getByLabelText("Indicadores de calidad")).getByText("960")).toBeInTheDocument();
    expect(imported).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Dataset analizado" })).toHaveValue("import-0f0f");
    expect(screen.getByText(/Se analiza tal como viene/)).toBeInTheDocument();
    expect(screen.getByText("OK/NOK reportado por la fuente vs. recalculado por especificación")).toBeInTheDocument();
    expect(screen.getByText("Solo NOK según la fuente").nextSibling).toHaveTextContent("27");
    // the customer's historical report is not mixed with an uploaded file
    expect(screen.queryByText("Ejemplo ilustrativo (cifras ficticias)")).not.toBeInTheDocument();
    // step provenance follows the dataset: a closed-period file, not the simulator
    expect(screen.getByText("Histórico")).toBeInTheDocument();
    expect(screen.queryByText("Simulado")).not.toBeInTheDocument();
    expect(screen.queryByText("Precalculado")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Descartar archivo/ }));
    expect(await within(await screen.findByLabelText("Indicadores de calidad")).findByText("Nido 4")).toBeInTheDocument();
    // Full import flow plus the lazy step chunk: more than the default 5 s on a loaded machine.
  }, 15_000);
});
