import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { ForbiddenPage } from "../../features/auth/ForbiddenPage";

// F5.4 (MI-33): route guards. RequireAuth existed as a mock stub in App.tsx
// (F5.M) with no redirect-back and no concept of "signed in but wrong role";
// this splits it into two composable guards so a route can require just a
// session, or a session plus specific roles.

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export function RequireRole({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  const allowed = user.roles.some((role) => roles.includes(role));
  if (!allowed) {
    return <ForbiddenPage />;
  }
  return <>{children}</>;
}
