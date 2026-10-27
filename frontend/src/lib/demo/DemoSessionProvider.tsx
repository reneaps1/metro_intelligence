import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { DEFAULT_QUALITY_FILTERS, type QualityFilters } from "../quality-analytics/filters";

// IQ-F1: client-side state shared by the demo steps (selected simulated
// scenario, IQ-F5 quality filters). "Restaurar escenario demo" only resets this
// state -- the simulator is stateless, so nothing in the database is touched.
export const DEFAULT_SCENARIO_ID = "normal";

interface DemoSession {
  scenarioId: string;
  setScenarioId: (id: string) => void;
  qualityFilters: QualityFilters;
  setQualityFilters: (update: (prev: QualityFilters) => QualityFilters) => void;
  /** Increments on every reset; steps key on it to drop their local state. */
  resetCount: number;
  reset: () => void;
}

const DemoSessionContext = createContext<DemoSession | null>(null);

export function DemoSessionProvider({ children }: { children: ReactNode }) {
  const [scenarioId, setScenarioId] = useState(DEFAULT_SCENARIO_ID);
  const [qualityFilters, setQualityFiltersState] = useState<QualityFilters>(DEFAULT_QUALITY_FILTERS);
  const [resetCount, setResetCount] = useState(0);

  const setQualityFilters = useCallback(
    (update: (prev: QualityFilters) => QualityFilters) => setQualityFiltersState(update),
    [],
  );

  const reset = useCallback(() => {
    setScenarioId(DEFAULT_SCENARIO_ID);
    setQualityFiltersState(DEFAULT_QUALITY_FILTERS);
    setResetCount((n) => n + 1);
  }, []);

  const value = useMemo(
    () => ({ scenarioId, setScenarioId, qualityFilters, setQualityFilters, resetCount, reset }),
    [scenarioId, qualityFilters, setQualityFilters, resetCount, reset],
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
