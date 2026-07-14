import { useEffect, type ReactElement, type ReactNode } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "../lib/auth/AuthProvider";

// F5.5 (MI-34): catalog screens read `useAuth().user` to gate edit UI, so
// their tests need an already-signed-in session. Driving the real login flow
// through AuthProvider (rather than injecting a fake context value) exercises
// the same code path LoginPage.test.tsx does, just skipping the form UI.
function AutoLogin({ email, password, children }: { email: string; password: string; children: ReactNode }) {
  const { login, status } = useAuth();
  useEffect(() => {
    login(email, password).catch(() => {
      // surfaced to the test via whatever it expects to find (or not find)
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  if (status !== "authenticated") return null;
  return <>{children}</>;
}

export function renderAuthed(
  ui: ReactElement,
  { email, password, route = "/" }: { email: string; password: string; route?: string },
) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[route]}>
        <AutoLogin email={email} password={password}>
          {ui}
        </AutoLogin>
      </MemoryRouter>
    </AuthProvider>,
  );
}
