import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../../lib/auth/AuthProvider";
import { RequireAuth } from "../../lib/auth/guards";
import { LoginPage } from "./LoginPage";
import { VALID_EMAIL, VALID_PASSWORD } from "../../test/server";

function renderApp(initialEntries: string[] = ["/login"]) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <div>Dashboard Home</div>
              </RequireAuth>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("LoginPage", () => {
  it("logs in with valid credentials and lands on the dashboard", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/email/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/password/i), VALID_PASSWORD);
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Dashboard Home")).toBeInTheDocument();
  });

  it("shows the backend's clean error message on invalid credentials and does not navigate", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/email/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(screen.queryByText("Dashboard Home")).not.toBeInTheDocument();
  });

  it("validates required fields on blur before allowing submit", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByLabelText(/email/i));
    await user.tab();

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Home")).not.toBeInTheDocument();
  });

  it("never writes any token to localStorage", async () => {
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");
    const user = userEvent.setup();
    renderApp();

    await user.type(screen.getByLabelText(/email/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/password/i), VALID_PASSWORD);
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    await screen.findByText("Dashboard Home");

    expect(setItemSpy).not.toHaveBeenCalled();
    setItemSpy.mockRestore();
  });

  it("redirects an unauthenticated visit to a protected route back to /login", () => {
    renderApp(["/dashboard"]);
    expect(screen.getByRole("heading", { name: /metro intelligence/i })).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Home")).not.toBeInTheDocument();
  });
});
