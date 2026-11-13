import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { renderAuthed } from "../../test/renderAuthed";
import { VALID_EMAIL, VALID_PASSWORD } from "../../test/server";
import { LinePanelPage } from "./LinePanelPage";

const login = { email: VALID_EMAIL, password: VALID_PASSWORD, route: "/demo/industrial-quality/panel-linea" };

describe("LinePanelPage", () => {
  it("opens on a calm stretch with the shift KPIs", async () => {
    renderAuthed(<LinePanelPage />, login);
    expect(await screen.findByText("PRODUCCIÓN NORMAL")).toBeInTheDocument();
    expect(screen.getByText("Piezas producidas")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reconocer/ })).toBeDisabled();
  });

  it("jumps to a real stop, acknowledges it and stops the line", async () => {
    const user = userEvent.setup();
    renderAuthed(<LinePanelPage />, login);
    await screen.findByText("PRODUCCIÓN NORMAL");

    await user.keyboard("s");
    expect(await screen.findByText("PARAR LÍNEA")).toBeInTheDocument();
    expect(screen.getByText("Sin reconocer")).toBeInTheDocument();

    await user.keyboard("r");
    await waitFor(() => expect(screen.getByText(/Reconocida · paso 1 de 4/)).toBeInTheDocument());

    await user.keyboard("a");
    expect(screen.getByRole("dialog", { name: "Registrar acción" })).toBeInTheDocument();
    await user.keyboard("1");
    expect(await screen.findByText("LÍNEA DETENIDA · CONTENCIÓN")).toBeInTheDocument();
    expect(screen.getAllByText("Línea detenida").length).toBeGreaterThan(0);
  });

  it("switches to the guided response view with one-touch actions", async () => {
    const user = userEvent.setup();
    renderAuthed(<LinePanelPage />, login);
    await screen.findByText("PRODUCCIÓN NORMAL");
    await user.keyboard("s");
    await screen.findByText("PARAR LÍNEA");
    await user.keyboard("3");
    expect(screen.getByText("Segregar desde")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Causa corregida — reanudar/ }));
    expect(await screen.findByText(/Sin acciones/)).toBeInTheDocument();
  });
});
