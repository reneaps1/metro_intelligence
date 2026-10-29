import { beforeEach, describe, expect, it, vi } from "vitest";
import { createEvent, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderAuthed } from "../../test/renderAuthed";
import { METROLOGIST_EMAIL, METROLOGIST_PASSWORD, SCENARIOS_FIXTURE } from "../../test/server";
import { DemoSessionProvider } from "../../lib/demo/DemoSessionProvider";
import { SignalExplorer } from "./SignalExplorer";
import { CorrelationPanel } from "./CorrelationPanel";
import { SIGNAL_DRAG_MIME } from "./SignalTree";

const CREDS = { email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD };
const SCENARIO = SCENARIOS_FIXTURE.items[1]; // thermal_drift

// Same jsdom layout stub as TrendChart.test.tsx so Recharts renders its SVG.
beforeEach(() => {
  vi.spyOn(Element.prototype, "getBoundingClientRect").mockReturnValue({
    width: 800,
    height: 200,
    top: 0,
    left: 0,
    right: 800,
    bottom: 200,
    x: 0,
    y: 0,
    toJSON: () => {},
  });
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(800);
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(200);
});

function renderExplorer() {
  return renderAuthed(
    <DemoSessionProvider>
      <SignalExplorer scenario={SCENARIO} />
    </DemoSessionProvider>,
    CREDS,
  );
}

describe("SignalExplorer", () => {
  it("adds three signals by button and separates tracks by unit", async () => {
    const user = userEvent.setup();
    renderExplorer();

    await user.click(await screen.findByRole("button", { name: "Agregar Temperatura de molde INY-01" }));
    await user.click(screen.getByRole("button", { name: "Agregar Presión de inyección INY-01" }));
    await user.click(screen.getByRole("button", { name: "Agregar Alarma activa INY-01" }));

    const table = screen.getByRole("table", { name: /señales en la gráfica/i });
    expect(within(table).getAllByRole("row")).toHaveLength(4); // header + 3
    expect(screen.getByRole("figure", { name: "Pista °C" })).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: "Pista bar" })).toBeInTheDocument();
    expect(screen.getByRole("figure", { name: "Pista 0/1" })).toBeInTheDocument();
    // Already-added signals cannot be added twice.
    expect(screen.getByRole("button", { name: "Agregar Temperatura de molde INY-01" })).toBeDisabled();
  });

  it("hides and removes signals", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await user.click(await screen.findByRole("button", { name: "Agregar Temperatura de molde INY-01" }));
    await user.click(screen.getByRole("button", { name: "Agregar Presión de inyección INY-01" }));

    await user.click(screen.getByRole("checkbox", { name: "Mostrar Presión de inyección INY-01" }));
    expect(screen.queryByRole("figure", { name: "Pista bar" })).not.toBeInTheDocument();
    expect(screen.getByRole("figure", { name: "Pista °C" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Quitar Temperatura de molde INY-01" }));
    expect(screen.queryByTestId("row-L1.INY-01.mold_temp")).not.toBeInTheDocument();
    expect(screen.getByTestId("row-L1.INY-01.injection_pressure")).toBeInTheDocument();
  });

  it("accepts a signal dropped from the tree", async () => {
    renderExplorer();
    const leaf = (await screen.findByText("Presión de inyección")).closest("li")!;
    const data = new Map<string, string>();
    const dataTransfer = {
      setData: (k: string, v: string) => data.set(k, v),
      getData: (k: string) => data.get(k) ?? "",
      effectAllowed: "",
      dropEffect: "",
    };
    fireEvent(leaf, Object.assign(createEvent.dragStart(leaf), { dataTransfer }));
    expect(data.get(SIGNAL_DRAG_MIME)).toBe("L1.INY-01.injection_pressure");
    const zone = screen.getByTestId("explorer-drop-zone");
    fireEvent(zone, Object.assign(createEvent.dragOver(zone), { dataTransfer }));
    fireEvent(zone, Object.assign(createEvent.drop(zone), { dataTransfer }));
    expect(await screen.findByTestId("row-L1.INY-01.injection_pressure")).toBeInTheDocument();
  });

  it("loads the suggested view and reads values at cursors A and B with Δt", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await user.click(await screen.findByRole("button", { name: /vista sugerida/i }));
    const row = await screen.findByTestId("row-L1.INY-01.mold_temp");

    const start = Date.parse(SCENARIO.start);
    const end = Date.parse(SCENARIO.end);
    fireEvent.change(screen.getByRole("slider", { name: "Posición del cursor A" }), {
      target: { value: String(start + (end - start) / 4) },
    });
    fireEvent.change(screen.getByRole("slider", { name: "Posición del cursor B" }), {
      target: { value: String((start + end) / 2) },
    });

    // Fixture series for the first signal: 100 at start, 110 at mid -> 105 at the
    // quarter (linear interpolation), Δ = 5.
    await waitFor(() => expect(within(row).getByText("105")).toBeInTheDocument());
    expect(within(row).getAllByText("110").length).toBeGreaterThan(0);
    expect(within(row).getByText("5")).toBeInTheDocument();
    expect(screen.getByText(/Δt: 2 h 00 min/)).toBeInTheDocument();
  });

  it("zooms with the toolbar and jumps to an event", async () => {
    const user = userEvent.setup();
    renderExplorer();
    expect(await screen.findByText(/Ventana: T\+00:00:00 → T\+08:00:00/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Acercar" }));
    expect(screen.getByText(/Ventana: T\+02:00:00 → T\+06:00:00/)).toBeInTheDocument();

    await user.click(await screen.findByRole("button", { name: "Ir al evento Alarma: temperatura de molde > 60 °C" }));
    expect(screen.getByText(/Ventana: T\+04:47:30 → T\+04:57:30/)).toBeInTheDocument();
    expect(screen.getByText(/A: T\+04:52:30/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Restablecer zoom" }));
    expect(screen.getByText(/Ventana: T\+00:00:00 → T\+08:00:00/)).toBeInTheDocument();
  });

  it("filters the tree by search text", async () => {
    const user = userEvent.setup();
    renderExplorer();
    await user.type(await screen.findByRole("searchbox", { name: /buscar señal/i }), "bar");
    expect(screen.getByText("Presión de inyección")).toBeInTheDocument();
    expect(screen.queryByText("Temperatura de molde")).not.toBeInTheDocument();
  });
});

describe("CorrelationPanel", () => {
  function renderPanel() {
    return renderAuthed(
      <DemoSessionProvider>
        <CorrelationPanel />
      </DemoSessionProvider>,
      CREDS,
    );
  }

  it("shows regression statistics and flags the imposed causal mechanism", async () => {
    renderPanel();
    expect(await screen.findByText("y = 12.37 − 0.000592 · x")).toBeInTheDocument();
    expect(screen.getByText("0.835")).toBeInTheDocument();
    expect(screen.getByText("-0.914")).toBeInTheDocument();
    expect(screen.getByText("Asociación lineal negativa fuerte.")).toBeInTheDocument();
    expect(screen.getByText(/relación causal impuesta/i)).toBeInTheDocument();
  });

  it("switches to time alignment and applies the optimal lag", async () => {
    const user = userEvent.setup();
    renderPanel();
    await user.click(await screen.findByRole("button", { name: /unión por tiempo: desfase de inspección/i }));
    const useBest = await screen.findByRole("button", { name: /usar desfase óptimo \(300 s\)/i });
    await user.click(useBest);
    await waitFor(() => expect(screen.getByRole("spinbutton", { name: "Desfase en s" })).toHaveValue(300));
  });
});
