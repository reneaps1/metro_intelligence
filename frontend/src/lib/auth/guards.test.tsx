import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./AuthProvider";
import { RequireRole } from "./guards";
import { LoginPage } from "../../features/auth/LoginPage";
import { VALID_EMAIL, VALID_PASSWORD } from "../../test/server";

// ME_FIXTURE (src/test/server.ts) is seeded with a single role:
// "quality_engineer".
function renderGuardedApp() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/admin"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/admin"
            element={
              <RequireRole roles={["admin"]}>
                <div>Admin Only</div>
              </RequireRole>
            }
          />
          <Route
            path="/qe"
            element={
              <RequireRole roles={["quality_engineer", "admin"]}>
                <div>QE Content</div>
              </RequireRole>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe("RequireRole", () => {
  it("redirects a signed-out visitor to /login, then back to the original route on success", async () => {
    const user = userEvent.setup();
    renderGuardedApp();

    // /admin requires auth first -- no session yet, so we land on /login.
    expect(screen.getByRole("heading", { name: /metro intelligence/i })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/email/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/password/i), VALID_PASSWORD);
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    // Signed in as quality_engineer, redirected back to /admin, which they don't have.
    expect(await screen.findByText("You don't have access to this page")).toBeInTheDocument();
    expect(screen.queryByText("Admin Only")).not.toBeInTheDocument();
  });

  it("renders the protected content when the signed-in user's role is allowed", async () => {
    const user = userEvent.setup();
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={["/qe"]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/qe"
              element={
                <RequireRole roles={["quality_engineer", "admin"]}>
                  <div>QE Content</div>
                </RequireRole>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );

    await user.type(screen.getByLabelText(/email/i), VALID_EMAIL);
    await user.type(screen.getByLabelText(/password/i), VALID_PASSWORD);
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("QE Content")).toBeInTheDocument();
  });
});
