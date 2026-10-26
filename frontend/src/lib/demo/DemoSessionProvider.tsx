import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

// IQ-F1: client-side state shared by the demo steps (selected simulated
// scenario today; filters later). "Restaurar escenario demo" only resets this
// state -- the simulator is stateless, so nothing in the database is touched.
export const DEFAULT_SCENARIO_ID = "normal";

interface DemoSession {
  scenarioId: string;
  setScenarioId: (id: string) => void;
  /** Increments on every reset; steps key on it to drop their local state. */
  resetCount: number;
  reset: () => void;
}

const DemoSessionContext = createContext<DemoSession | null>(null);

export function DemoSessionProvider({ children }: { children: ReactNode }) {
  const [scenarioId, setScenarioId] = useState(DEFAULT_SCENARIO_ID);
  const [resetCount, setResetCount] = useState(0);

  const reset = useCallback(() => {
    setScenarioId(DEFAULT_SCENARIO_ID);
    setResetCount((n) => n + 1);
  }, []);

  const value = useMemo(
    () => ({ scenarioId, setScenarioId, resetCount, reset }),
    [scenarioId, resetCount, reset],
  );
  return <DemoSessionContext.Provider value={value}>{children}</DemoSessionContext.Provider>;
}

export function useDemoSession(): DemoSession {
  const session = useContext(DemoSessionContext);
  if (!session) {
    throw new Error("useDemoSession must be used inside DemoSessionProvider");
  }
  return session;
}
