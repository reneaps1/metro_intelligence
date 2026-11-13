import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
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
        <Route path="/process" element={<p>Process home</p>} />
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
    expect(await screen.findByText("Process")).toBeInTheDocument();
    expect(screen.queryByText("Demo industrial")).not.toBeInTheDocument();

    renderDemo();
    expect(await screen.findByText("Process home")).toBeInTheDocument();
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

    await user.click(await screen.findByRole("button", { name: "Iniciar recorrido" }));
    expect(await screen.findByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();
    expect(within(screen.getByRole("group", { name: "Recorrido" })).getByText("1 / 3")).toBeInTheDocument();
    // Step 1 is lazy-loaded (IQ-F8): the first import can take a while under a parallel run.
    expect(await screen.findByLabelText("Indicadores de calidad", {}, { timeout: 5000 })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /siguiente: exploración dimensional/i }));
    expect(await screen.findByRole("heading", { name: "Exploración dimensional" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /anterior: diagnóstico de calidad/i }));
    expect(await screen.findByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();
    // Walks three steps, one of them lazy-loaded: over the default 5 s on a loaded machine.
  }, 15_000);

  it("project tree lists only the quality, process and predictive steps", async () => {
    server.use(industrialMetaHandler());
    renderDemo();
    const nav = await screen.findByRole("navigation", { name: /pasos de la demo/i });
    expect(within(nav).getAllByRole("link")).toHaveLength(3);
    expect(within(nav).getAllByRole("heading").map((h) => h.textContent)).toEqual(["Calidad", "Predictivo"]);
    const tree = screen.getByRole("complementary", { name: "Árbol del proyecto" });
    expect(within(tree).getByText("Pantallas de planta")).toBeInTheDocument();
    expect(within(tree).getByRole("link", { name: /panel de calidad en línea/i })).toHaveAttribute(
      "href",
      "/demo/industrial-quality/panel-linea",
    );
    expect(within(tree).queryByText(/Activos/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Panel en línea" })).toBeInTheDocument();
    // the simulated process scenario and its alarms are gone with the process steps
    expect(screen.queryByRole("button", { name: /^escenario/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^alarmas/i })).not.toBeInTheDocument();
  });

  it.each(["context", "iiot", "correlation", "integration"])("the removed %s step falls back to the demo home", async (stepId) => {
    server.use(industrialMetaHandler());
    renderDemo(`/demo/industrial-quality/${stepId}`);
    expect(await screen.findByRole("button", { name: "Iniciar recorrido" })).toBeInTheDocument();
  });

  it("home shows the selected part's figures and the walkthrough table, each linked to its step", async () => {
    server.use(industrialMetaHandler());
    renderDemo();
    const strip = await screen.findByRole("region", { name: "Indicadores de la pieza" });
    const pieces = await within(strip).findByRole("link", { name: /piezas medidas/i });
    await waitFor(() => expect(pieces).not.toHaveTextContent("…"));
    expect(pieces).toHaveAttribute("href", "/demo/industrial-quality/quality");
    expect(within(strip).getByRole("link", { name: /variable con más nok/i })).toHaveAttribute(
      "href",
      "/demo/industrial-quality/dimensional",
    );
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(1 + 3 + 1);
    expect(within(table).getByRole("link", { name: "IA predictiva y oleadas NOK" })).toBeInTheDocument();
    expect(within(table).getAllByTitle(/simulador de proceso/i)[0]).toHaveTextContent("Simulado");
    // no marketing copy, quick-access cards or origin legend on the home
    expect(screen.queryByText(/accesos rápidos/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/cómo leer el origen/i)).not.toBeInTheDocument();
  });

  it("unknown step falls back to the demo home", async () => {
    server.use(industrialMetaHandler());
    renderDemo("/demo/industrial-quality/nope");
    expect(await screen.findByRole("button", { name: "Iniciar recorrido" })).toBeInTheDocument();
  });
});

describe("DemoShell workbench", () => {
  it("opens a predictive view from a direct link, shows it in the path and moves between views with the arrow keys", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo("/demo/industrial-quality/ai?vista=cusum");

    const cusum = await screen.findByRole("tab", { name: "CUSUM" }, { timeout: 5000 });
    expect(cusum).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("navigation", { name: "Ruta" })).toHaveTextContent("Predictivo›IA predictiva›CUSUM");
    cusum.focus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Oleadas NOK" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Oleadas NOK" })).toHaveFocus();
    expect(screen.queryByRole("tab", { name: "What-if" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Fallas de máquina" })).not.toBeInTheDocument();
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Modelos ML/DL" })).toHaveAttribute("aria-selected", "true");
  });

  it("hides the tree and the inspector and remembers it", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    const { unmount } = renderDemo("/demo/industrial-quality/quality");

    await user.click(await screen.findByRole("button", { name: "Árbol del proyecto" }));
    expect(screen.queryByRole("navigation", { name: /pasos de la demo/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Inspector" }));
    expect(screen.queryByRole("complementary", { name: "Inspector" })).not.toBeInTheDocument();
    // the document area is untouched
    expect(screen.getByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();

    unmount();
    renderDemo("/demo/industrial-quality/quality");
    const treeToggle = await screen.findByRole("button", { name: "Árbol del proyecto" });
    expect(treeToggle).toHaveAttribute("aria-pressed", "false");
    await user.click(treeToggle);
    expect(screen.getByRole("navigation", { name: /pasos de la demo/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Inspector" }));
  });

  it("inspector explains the provenance of the open view", async () => {
    server.use(industrialMetaHandler());
    renderDemo("/demo/industrial-quality/dimensional");
    const inspector = await screen.findByRole("complementary", { name: "Inspector" });
    expect(within(inspector).getByText(ORIGIN_INFO.SIMULATED.description)).toBeInTheDocument();
    expect(within(inspector).getByText("2 de 3")).toBeInTheDocument();
    expect(within(inspector).queryByText("Escenario simulado")).not.toBeInTheDocument();
  });

  it("walks the demo with Av Pág / Re Pág (presentation clicker)", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo("/demo/industrial-quality/quality");

    expect(await screen.findByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();
    await user.keyboard("{PageDown}");
    expect(await screen.findByRole("heading", { name: "Exploración dimensional" })).toBeInTheDocument();
    await user.keyboard("{PageUp}");
    expect(await screen.findByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();
  });

  it("menu bar switches the theme and opens the line panel", async () => {
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

    expect(screen.queryByRole("menuitem", { name: "Escenario" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "Ver" }));
    expect(screen.getByRole("menuitem", { name: "Panel de calidad en línea" })).toBeInTheDocument();
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
