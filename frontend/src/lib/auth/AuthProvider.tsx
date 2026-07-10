import { createContext, useContext, useState, type ReactNode } from "react";
import { DEMO_USERS } from "../mock/fixtures";
import type { DemoUser } from "../mock/types";

// Mocked auth: a role selector, not a real credential check. Real JWT auth
// lands in F4.2/F5.4; this stands in so the golden path is navigable
// role-aware (CLAUDE.md §0).
const STORAGE_KEY = "metro-intelligence.user";

interface AuthContextValue {
  user: DemoUser | null;
  login: (userId: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<DemoUser | null>(() => {
    const storedId = localStorage.getItem(STORAGE_KEY);
    return DEMO_USERS.find((u) => u.id === storedId) ?? null;
  });

  const login = (userId: string) => {
    const found = DEMO_USERS.find((u) => u.id === userId);
    if (!found) return;
    setUser(found);
    localStorage.setItem(STORAGE_KEY, found.id);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
