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
import { formatOffset } from "./steps/IiotSourcesStep";

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
    expect(screen.getByText("Paso 1 de 7")).toBeInTheDocument();
    expect(screen.getByText("Trazabilidad ciclo ↔ pieza")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /siguiente: diagnóstico de calidad/i }));
    expect(await screen.findByRole("heading", { name: "Diagnóstico de calidad" })).toBeInTheDocument();
    expect(screen.getByText(/en construcción/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /anterior/i }));
    expect(await screen.findByRole("heading", { name: "Contexto industrial" })).toBeInTheDocument();
  });

  it("stepper lists the seven steps", async () => {
    server.use(industrialMetaHandler());
    renderDemo();
    const nav = await screen.findByRole("navigation", { name: /pasos de la demo/i });
    expect(within(nav).getAllByRole("link")).toHaveLength(7);
  });

  it("quick access selects the thermal drift scenario and reset restores normal", async () => {
    server.use(industrialMetaHandler());
    const user = userEvent.setup();
    renderDemo();

    await user.click(await screen.findByRole("button", { name: /explorar deriva de temperatura/i }));
    expect(await screen.findByRole("heading", { name: "Laboratorio IIoT" })).toBeInTheDocument();
    const thermal = await screen.findByRole("button", { name: /deriva térmica del molde/i });
    expect(thermal).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByText("Alarma: temperatura de molde > 60 °C")).toBeInTheDocument();
    expect(screen.getByText("T+04:52")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /restaurar escenario demo/i }));
    expect(screen.getByRole("status")).toHaveTextContent(/escenario demo restaurado/i);
    const normal = await screen.findByRole("button", { name: /operación normal estable/i });
    expect(normal).toHaveAttribute("aria-pressed", "true");
  });

  it("unknown step falls back to the demo home", async () => {
    server.use(industrialMetaHandler());
    renderDemo("/demo/industrial-quality/nope");
    expect(await screen.findByRole("button", { name: /iniciar demo/i })).toBeInTheDocument();
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

describe("formatOffset", () => {
  it("formats the offset from the scenario start", () => {
    expect(formatOffset("2026-10-20T06:00:00Z", "2026-10-20T08:05:00Z")).toBe("T+02:05");
    expect(formatOffset("2026-10-20T06:00:00Z", "2026-10-20T06:00:00Z")).toBe("T+00:00");
  });
});
