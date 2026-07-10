import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import {
  CHARACTERISTICS,
  MEASUREMENT_RUNS,
  PARTS,
  PROCESS_EVENTS,
  RECOMMENDATIONS,
  RISK_ASSESSMENTS,
  getSeriesForCharacteristic,
} from "./fixtures";
import type { Recommendation, RecommendationState } from "./types";

// Single data-access surface for the whole app. Right now every read comes
// from static fixtures (CLAUDE.md §0); when F4's real API lands, only the
// implementations inside this provider change — callers keep using
// useDemoData() unchanged.
interface DemoDataContextValue {
  parts: typeof PARTS;
  characteristics: typeof CHARACTERISTICS;
  riskAssessments: typeof RISK_ASSESSMENTS;
  recommendations: Recommendation[];
  processEvents: typeof PROCESS_EVENTS;
  measurementRuns: typeof MEASUREMENT_RUNS;
  getSeries: typeof getSeriesForCharacteristic;
  decideRecommendation: (id: string, state: RecommendationState, decidedBy: string, comment: string) => void;
}

const DemoDataContext = createContext<DemoDataContextValue | null>(null);

export function DemoDataProvider({ children }: { children: ReactNode }) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>(RECOMMENDATIONS);

  const decideRecommendation = (
    id: string,
    state: RecommendationState,
    decidedBy: string,
    comment: string
  ) => {
    setRecommendations((prev) =>
      prev.map((rec) =>
        rec.id === id
          ? {
              ...rec,
              state,
              decidedBy,
              decidedAt: new Date().toISOString(),
              decisionComment: comment,
            }
          : rec
      )
    );
  };

  const value = useMemo<DemoDataContextValue>(
    () => ({
      parts: PARTS,
      characteristics: CHARACTERISTICS,
      riskAssessments: RISK_ASSESSMENTS,
      recommendations,
      processEvents: PROCESS_EVENTS,
      measurementRuns: MEASUREMENT_RUNS,
      getSeries: getSeriesForCharacteristic,
      decideRecommendation,
    }),
    [recommendations]
  );

  return <DemoDataContext.Provider value={value}>{children}</DemoDataContext.Provider>;
}

export function useDemoData(): DemoDataContextValue {
  const ctx = useContext(DemoDataContext);
  if (!ctx) throw new Error("useDemoData must be used within DemoDataProvider");
  return ctx;
}
