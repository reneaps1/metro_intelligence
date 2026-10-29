import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { renderAuthed } from "../../test/renderAuthed";
import { industrialMetaHandler, METROLOGIST_EMAIL, METROLOGIST_PASSWORD, server } from "../../test/server";
import { EditionProvider, RequireEdition } from "../../lib/edition/EditionProvider";
import { Sidebar } from "../../components/ui/Sidebar";
import { DATA_ORIGINS, ORIGIN_INFO } from "../../lib/demo/origin";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { render } from "@testing-library/react";
import { DemoShell } from "./DemoShell";
import { DemoHomePage } from "./DemoHomePage";
import { DemoStepPage } from "./DemoStepPage";
import { formatRelative } from "../../lib/industrial-signals/explorer";

const CREDS = { email: METROLOGIST_EMAIL, password: METROLOGIST_PASSWORD };

function renderDemo(route = "/demo/industrial-quality") {
  return renderAuthed(
    <EditionProvider>
      <Routes>
        <Route path="/dashboard" element={<p>Dashboard original</p>} />
        <Route
          path="/demo/industrial-quality"
          element={
            <RequireEdition edition="industrial">
              <DemoShell />
            </RequireEdition>
          }
        >
          <Route index element={<DemoHomePage />} />
          <Route path=":stepId" element={<DemoStepPage />} />
        </Route>
      </Routes>
    </EditionProvider>,
    { ...CREDS, route },
  );
}

describe("edition gating", () => {
  it("metrology edition hides the demo entry and redirects its routes", async () => {
    renderAuthed(
      <EditionProvider>
        <Sidebar />
      </EditionProvider>,
      CREDS,
    );
    expect(await screen.findByText("Live Monitor")).toBeInTheDocument();
    expect(screen.queryByText("Demo industrial")).not.toBeInTheDocument();

    renderDemo();
    expect(await screen.findByText("Dashboard original")).toBeInTheDocument();
  });

  it("industrial edition shows the demo entry in the sidebar", async () => {
    server.use(industrialMetaHandler());
    renderAuthed(
      <EditionProvider>
        <Sidebar />
      </EditionProvider>,
      CREDS,
    );
    expect(await screen.findByText("Demo industrial")).toBeInTheDocument();
  });
});

describe("DemoShell walkthrough", () => {
  it("starts the demo from the home page and walks forward and back", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo();

    await user.click(await screen.findByRole("button", { name: /iniciar demo/i }));
    expect(await screen.findByRole("heading", { name: "Contexto industrial" })).toBeInTheDocument();
    expect(within(screen.getByRole("group", { name: "Recorrido" })).getByText("1 / 7")).toBeInTheDocument();
    expect(screen.getByText("Trazabilidad ciclo ↔ pieza")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /siguiente: diagnóstico de calidad/i }));
    expect(await screen.findByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();
    // Step 2 is lazy-loaded (IQ-F8): the first import can take a while under a parallel run.
    expect(await screen.findByLabelText("Indicadores de calidad", {}, { timeout: 5000 })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /anterior: contexto industrial/i }));
    expect(await screen.findByRole("heading", { name: "Contexto industrial" })).toBeInTheDocument();
    // Walks three steps, one of them lazy-loaded: over the default 5 s on a loaded machine.
  }, 15_000);

  it("project tree lists the seven steps in their groups", async () => {
    server.use(industrialMetaHandler());
    renderDemo();
    const nav = await screen.findByRole("navigation", { name: /pasos de la demo/i });
    expect(within(nav).getAllByRole("link")).toHaveLength(7);
    for (const group of ["Recorrido", "Calidad", "Proceso", "Predictivo", "Planta"]) {
      expect(within(nav).getByRole("heading", { name: group })).toBeInTheDocument();
    }
  });

  it("quick access selects the thermal drift scenario and reset restores normal", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo();

    await user.click(await screen.findByRole("button", { name: /explorar deriva de temperatura/i }));
    expect(await screen.findByRole("heading", { name: "Laboratorio IIoT" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /^escenario deriva térmica del molde/i })).toBeInTheDocument();
    // Step 4 is lazy-loaded (IQ-F8): give the explorer time under a parallel run.
    expect(await screen.findByText("Alarma: temperatura de molde > 60 °C", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText("T+04:52")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alarmas: 1 activas, 1 sin reconocer" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^escenario/i }));
    await user.click(within(screen.getByRole("dialog", { name: "Escenario simulado" })).getByRole("button", { name: "Restaurar escenario demo" }));
    expect(screen.getByRole("status")).toHaveTextContent(/escenario demo restaurado/i);
    expect(await screen.findByRole("button", { name: /^escenario operación normal estable/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alarmas: 0 activas, 0 sin reconocer" })).toBeInTheDocument();
  }, 15_000);

  it("step 7 contrasts today's demo with a real integration and keeps decisions human", async () => {
    server.use(industrialMetaHandler());
    renderDemo("/demo/industrial-quality/integration");
    const table = await screen.findByLabelText("Hoy vs. con integración");
    expect(within(table).getByText("Señales de proceso")).toBeInTheDocument();
    expect(within(table).getAllByText("Simulado").length).toBeGreaterThan(0);
    expect(screen.getByText("Decisión humana")).toBeInTheDocument();
    expect(screen.getByText(/La capa IIoT mostrada aquí es simulada/)).toBeInTheDocument();
  });

  it("unknown step falls back to the demo home", async () => {
    server.use(industrialMetaHandler());
    renderDemo("/demo/industrial-quality/nope");
    expect(await screen.findByRole("button", { name: /iniciar demo/i })).toBeInTheDocument();
  });
});

describe("DemoShell workbench", () => {
  it("applies a scenario in two steps, without leaving the view, and undoes it", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo("/demo/industrial-quality/context");

    await user.click(await screen.findByRole("button", { name: /^escenario operación normal estable/i }));
    const dialog = screen.getByRole("dialog", { name: "Escenario simulado" });
    const apply = within(dialog).getByRole("button", { name: "Aplicar escenario" });
    expect(apply).toBeDisabled();
    await user.click(within(dialog).getByRole("radio", { name: /deriva térmica del molde/i }));
    await user.click(apply);

    expect(screen.getByRole("status")).toHaveTextContent("Escenario aplicado: Deriva térmica del molde.");
    // the scenario never navigates away from the open view
    expect(screen.getByRole("heading", { name: "Contexto industrial" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alarmas: 1 activas, 1 sin reconocer" })).toBeInTheDocument();
    expect(screen.getByLabelText("Última acción")).toHaveTextContent("Escenario simulado: Deriva térmica del molde");

    await user.click(screen.getByRole("button", { name: "Deshacer" }));
    expect(screen.getByRole("button", { name: /^escenario operación normal estable/i })).toBeInTheDocument();
  });

  it("lists the simulated alarms and acknowledges them", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo("/demo/industrial-quality/context");

    await user.click(await screen.findByRole("button", { name: /^escenario/i }));
    await user.click(screen.getByRole("radio", { name: /deriva térmica del molde/i }));
    await user.click(screen.getByRole("button", { name: "Aplicar escenario" }));

    await user.click(screen.getByRole("button", { name: /^alarmas/i }));
    const summary = screen.getByRole("dialog", { name: "Resumen de alarmas" });
    expect(within(summary).getByText("Temperatura de molde en deriva ascendente")).toBeInTheDocument();
    expect(within(summary).getByText("INY01.TMOLDE")).toBeInTheDocument();
    await user.click(within(summary).getByRole("button", { name: "Reconocer todas" }));
    expect(screen.getByRole("button", { name: "Alarmas: 1 activas, 0 sin reconocer" })).toBeInTheDocument();
  });

  it("opens a step 6 view from a direct link, shows it in the path and moves between views with the arrow keys", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo("/demo/industrial-quality/ai?vista=cusum");

    const cusum = await screen.findByRole("tab", { name: "CUSUM" }, { timeout: 5000 });
    expect(cusum).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("navigation", { name: "Ruta" })).toHaveTextContent("Predictivo›IA predictiva›CUSUM");
    cusum.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "What-if" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "What-if" })).toHaveFocus();
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Modelos ML/DL" })).toHaveAttribute("aria-selected", "true");
  });

  it("hides the tree and the inspector and remembers it", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    const { unmount } = renderDemo("/demo/industrial-quality/context");

    await user.click(await screen.findByRole("button", { name: "Árbol del proyecto" }));
    expect(screen.queryByRole("navigation", { name: /pasos de la demo/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Inspector" }));
    expect(screen.queryByRole("complementary", { name: "Inspector" })).not.toBeInTheDocument();
    // the document area is untouched
    expect(screen.getByRole("heading", { name: "Contexto industrial" })).toBeInTheDocument();

    unmount();
    renderDemo("/demo/industrial-quality/context");
    const treeToggle = await screen.findByRole("button", { name: "Árbol del proyecto" });
    expect(treeToggle).toHaveAttribute("aria-pressed", "false");
    await user.click(treeToggle);
    expect(screen.getByRole("navigation", { name: /pasos de la demo/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Inspector" }));
  });

  it("inspector explains the provenance and the simulated scenario of the open view", async () => {
    server.use(industrialMetaHandler());
    renderDemo("/demo/industrial-quality/iiot");
    const inspector = await screen.findByRole("complementary", { name: "Inspector" });
    expect(within(inspector).getByText(ORIGIN_INFO.SIMULATED.description)).toBeInTheDocument();
    expect(await within(inspector).findByText("process-sim-1.0.0")).toBeInTheDocument();
    expect(within(inspector).getByText("4 de 7")).toBeInTheDocument();
  });

  it("walks the demo with Av Pág / Re Pág (presentation clicker)", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo("/demo/industrial-quality/context");

    expect(await screen.findByRole("heading", { name: "Contexto industrial" })).toBeInTheDocument();
    await user.keyboard("{PageDown}");
    expect(await screen.findByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();
    await user.keyboard("{PageUp}");
    expect(await screen.findByRole("heading", { name: "Contexto industrial" })).toBeInTheDocument();
  });

  it("menu bar switches the theme and opens the scenario control", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo();

    await user.click(await screen.findByRole("menuitem", { name: "Ver" }));
    await user.click(screen.getByRole("menuitemcheckbox", { name: "Tema oscuro" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    await user.click(screen.getByRole("menuitem", { name: "Ver" }));
    expect(screen.getByRole("menuitemcheckbox", { name: "Tema oscuro" })).toHaveAttribute("aria-checked", "true");
    await user.click(screen.getByRole("menuitemcheckbox", { name: "Tema oscuro" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");

    await user.click(screen.getByRole("menuitem", { name: "Escenario" }));
    await user.click(screen.getByRole("menuitem", { name: "Cambiar escenario…" }));
    expect(screen.getByRole("dialog", { name: "Escenario simulado" })).toBeInTheDocument();
  });
});

describe("OriginBadge", () => {
  it("renders every data origin with its explanation", () => {
    render(
      <>
        {DATA_ORIGINS.map((origin) => (
          <OriginBadge key={origin} origin={origin} />
        ))}
      </>,
    );
    for (const origin of DATA_ORIGINS) {
      const badge = screen.getByText(ORIGIN_INFO[origin].label);
      expect(badge).toHaveAttribute("title", ORIGIN_INFO[origin].description);
    }
  });
});

describe("formatRelative", () => {
  it("formats the offset from the scenario start", () => {
    const origin = Date.parse("2026-10-20T06:00:00Z");
    expect(formatRelative(Date.parse("2026-10-20T08:05:00Z"), origin)).toBe("T+02:05");
    expect(formatRelative(origin, origin)).toBe("T+00:00");
    expect(formatRelative(Date.parse("2026-10-20T10:52:30Z"), origin, true)).toBe("T+04:52:30");
  });
});
