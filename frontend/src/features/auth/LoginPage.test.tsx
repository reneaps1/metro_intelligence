import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../../lib/auth/AuthProvider";
import { RequireAuth } from "../../lib/auth/guards";
import { LoginPage } from "./LoginPage";
import { http, HttpResponse } from "msw";
import { server, VALID_EMAIL, VALID_PASSWORD } from "../../test/server";

function renderApp(initialEntries: string[] = ["/login"]) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/process"
            element={
              <RequireAuth>
                <div>Process Home</div>
              </RequireAuth>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("LoginPage", () => {
  it("logs in with valid credentials and lands on the process view", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/correo/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/contraseña/i), VALID_PASSWORD);
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByText("Process Home")).toBeInTheDocument();
  });

  it("shows the backend's clean error message on invalid credentials and does not navigate", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/correo/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/contraseña/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contraseña incorrectos.");
    expect(screen.queryByText("Process Home")).not.toBeInTheDocument();
  });

  it("tells a rejected visitor that earlier demo accesses expired, and lets them dismiss it", async () => {
    const user = userEvent.setup();
    renderApp();
    expect(screen.queryByRole("status")).not.toBeInTheDocument(); // not before a rejected sign-in

    await user.type(screen.getByLabelText(/correo/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/contraseña/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("¿Tu acceso demo dejó de funcionar?");
    expect(notice).toHaveTextContent(
      "Los accesos demo anteriores ya expiraron. Para solicitar uno nuevo, ponte en contacto con nosotros.",
    );

    await user.click(screen.getByRole("button", { name: "Cerrar aviso" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("also shows the notice when the account is locked after too many rejected sign-ins", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/auth/login", () =>
        HttpResponse.json({ detail: "Too many attempts." }, { status: 429 }),
      ),
    );
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/correo/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/contraseña/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Demasiados intentos. Espera unos minutos y vuelve a intentar.");
    expect(screen.getByRole("status")).toHaveTextContent("¿Tu acceso demo dejó de funcionar?");
  });

  it("says in Spanish that the server did not answer, without the expired-access notice", async () => {
    server.use(http.post("http://localhost:8000/api/v1/auth/login", () => HttpResponse.error()));
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/correo/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/contraseña/i), VALID_PASSWORD);
    await user.click(screen.getByRole("button", { name: /entrar/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo conectar con el servidor. Vuelve a intentar en unos segundos.",
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("validates required fields on blur before allowing submit", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByLabelText(/correo/i));
    await user.tab();

    expect(await screen.findByText(/falta el correo/i)).toBeInTheDocument();
    expect(screen.queryByText("Process Home")).not.toBeInTheDocument();
  });

  it("never writes any token to localStorage", async () => {
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/correo/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/contraseña/i), VALID_PASSWORD);
    await user.click(screen.getByRole("button", { name: /entrar/i }));
    await screen.findByText("Process Home");

    expect(setItemSpy).not.toHaveBeenCalled();
    setItemSpy.mockRestore();
  });

  it("redirects an unauthenticated visit to a protected route back to /login", () => {
    renderApp(["/process"]);
    expect(screen.getByRole("heading", { name: /partview/i })).toBeInTheDocument();
    expect(screen.queryByText("Process Home")).not.toBeInTheDocument();
  });
});
