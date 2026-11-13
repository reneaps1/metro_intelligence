import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { fetchMeta, type Edition } from "./api";

export const DEFAULT_CLIENT_LABEL = "Cliente demo";

interface EditionState {
  edition: Edition;
  clientLabel: string;
  loading: boolean;
}

// Fail-closed default: until /meta answers (or if it fails), the app behaves
// as the metrology edition and never shows industrial modules.
const EditionContext = createContext<EditionState>({
  edition: "metrology",
  clientLabel: DEFAULT_CLIENT_LABEL,
  loading: false,
});

export function EditionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<EditionState>({
    edition: "metrology",
    clientLabel: DEFAULT_CLIENT_LABEL,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    fetchMeta()
      .then((meta) => {
        if (!cancelled) {
          setState({ edition: meta.edition, clientLabel: meta.client_label ?? DEFAULT_CLIENT_LABEL, loading: false });
        }
      })
      .catch(() => {
        if (!cancelled) setState((s) => ({ ...s, loading: false }));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return <EditionContext.Provider value={state}>{children}</EditionContext.Provider>;
}

export function useEdition(): EditionState {
  return useContext(EditionContext);
}

export function RequireEdition({ edition, children }: { edition: Edition; children: ReactNode }) {
  const { edition: current, loading } = useEdition();
  if (loading) {
    return <p className="text-sm text-text-secondary">Cargando…</p>;
  }
  if (current !== edition) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}
