import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { DEFAULT_QUALITY_FILTERS, type QualityFilters } from "../quality-analytics/filters";

// IQ-F1: client-side state shared by the demo steps (selected simulated
// scenario, IQ-F5 quality filters, acknowledged simulated alarms). "Restaurar
// escenario demo" only resets this state -- the simulator is stateless, so
// nothing in the database is touched.
export const DEFAULT_SCENARIO_ID = "normal";

interface DemoSession {
  scenarioId: string;
  setScenarioId: (id: string) => void;
  qualityFilters: QualityFilters;
  setQualityFilters: (update: (prev: QualityFilters) => QualityFilters) => void;
  /** Ids of the simulated alarms the presenter acknowledged. */
  acknowledgedAlarms: string[];
  acknowledgeAlarms: (ids: string[]) => void;
  /** Increments on every reset; steps key on it to drop their local state. */
  resetCount: number;
  reset: () => void;
  /** IQ-F12: dataset the predictive lab (step 6) currently analyses; null = synthetic demo. */
  aiDatasetId: string | null;
  setAiDatasetId: (id: string | null) => void;
}

const DemoSessionContext = createContext<DemoSession | null>(null);

export function DemoSessionProvider({ children }: { children: ReactNode }) {
  const [scenarioId, setScenarioId] = useState(DEFAULT_SCENARIO_ID);
  const [qualityFilters, setQualityFiltersState] = useState<QualityFilters>(DEFAULT_QUALITY_FILTERS);
  const [acknowledgedAlarms, setAcknowledgedAlarms] = useState<string[]>([]);
  const [resetCount, setResetCount] = useState(0);
  const [aiDatasetId, setAiDatasetId] = useState<string | null>(null);

  const setQualityFilters = useCallback(
    (update: (prev: QualityFilters) => QualityFilters) => setQualityFiltersState(update),
    [],
  );

  const acknowledgeAlarms = useCallback(
    (ids: string[]) => setAcknowledgedAlarms((prev) => Array.from(new Set([...prev, ...ids]))),
    [],
  );

  const reset = useCallback(() => {
    setScenarioId(DEFAULT_SCENARIO_ID);
    setQualityFiltersState(DEFAULT_QUALITY_FILTERS);
    setAcknowledgedAlarms([]);
    setResetCount((n) => n + 1);
  }, []);

  const value = useMemo(
    () => ({
      scenarioId,
      setScenarioId,
      qualityFilters,
      setQualityFilters,
      acknowledgedAlarms,
      acknowledgeAlarms,
      resetCount,
      reset,
      aiDatasetId,
      setAiDatasetId,
    }),
    [scenarioId, qualityFilters, setQualityFilters, acknowledgedAlarms, acknowledgeAlarms, resetCount, reset, aiDatasetId],
  );
  return <DemoSessionContext.Provider value={value}>{children}</DemoSessionContext.Provider>;
}

/** For components that may render outside the demo shell (e.g. isolated tests). */
export function useOptionalDemoSession(): DemoSession | null {
  return useContext(DemoSessionContext);
}

export function useDemoSession(): DemoSession {
  const session = useContext(DemoSessionContext);
  if (!session) {
    throw new Error("useDemoSession must be used inside DemoSessionProvider");
  }
  return session;
}
