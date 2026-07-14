import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { loginRequest, logoutRequest, meRequest, onSessionExpired, setTokens, type MeResponse } from "../api";

// F5.4 (MI-33): real JWT session, replacing F5.M's role-selector mock. The
// public shape of useAuth() (user/login/logout) is unchanged so the rest of
// the app (Topbar, RiskPage, ImportPage) didn't need to change.
export interface SessionUser {
  id: string;
  email: string;
  displayName: string;
  roles: string[];
  /** Primary role for the existing single-role UI checks (every demo user has exactly one role). */
  role: string;
}

export type AuthStatus = "anonymous" | "authenticating" | "authenticated";

interface AuthContextValue {
  user: SessionUser | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function toSessionUser(me: MeResponse): SessionUser {
  return {
    id: me.id,
    email: me.email,
    displayName: me.display_name,
    roles: me.roles,
    role: me.roles[0] ?? "viewer",
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // No persisted session to restore on mount: tokens live only in memory
  // (see lib/api.ts), so every fresh page load starts anonymous by
  // construction -- there is no stale/zombie session state to reconcile.
  const [user, setUser] = useState<SessionUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("anonymous");

  const clearSession = useCallback(() => {
    setTokens(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  useEffect(() => {
    onSessionExpired(clearSession);
    return () => onSessionExpired(null);
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string) => {
    setStatus("authenticating");
    try {
      const tokens = await loginRequest(email, password);
      setTokens(tokens);
      const me = await meRequest();
      setUser(toSessionUser(me));
      setStatus("authenticated");
    } catch (err) {
      setTokens(null);
      setStatus("anonymous");
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    clearSession();
  }, [clearSession]);

  return <AuthContext.Provider value={{ user, status, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
