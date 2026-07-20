import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import {
  CHARACTERISTICS,
  IMPORT_SCENARIOS,
  MEASUREMENT_RUNS,
  PARTS,
  PROCESS_EVENTS,
  RECOMMENDATIONS,
  RISK_ASSESSMENTS,
  getSeriesForCharacteristic,
} from "./fixtures";
import { simulateNewPoints } from "./generator";
import type {
  ActionOutcomeStatus,
  ImportedFileRecord,
  MeasurementPoint,
  MeasurementRunSummary,
  Recommendation,
  RecommendationState,
} from "./types";

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
  measurementRuns: MeasurementRunSummary[];
  importScenarios: typeof IMPORT_SCENARIOS;
  importedFiles: ImportedFileRecord[];
  getSeries: (characteristicId: string) => MeasurementPoint[];
  decideRecommendation: (id: string, state: RecommendationState, decidedBy: string, comment: string) => void;
  addActionTaken: (
    recommendationId: string,
    input: { description: string; outcomeStatus: ActionOutcomeStatus }
  ) => void;
  importFile: (scenarioId: string) => string;
}

const DemoDataContext = createContext<DemoDataContextValue | null>(null);

function fakeSha256(seed: string): string {
  let h1 = 0x811c9dc5;
  for (let i = 0; i < seed.length; i++) {
    h1 = Math.imul(h1 ^ seed.charCodeAt(i), 16777619);
  }
  const base = Math.abs(h1).toString(16).padStart(8, "0");
  return (base + base + base + base + base + base + base + base).slice(0, 64);
}

export function DemoDataProvider({ children }: { children: ReactNode }) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>(RECOMMENDATIONS);
  const [measurementRuns, setMeasurementRuns] = useState<MeasurementRunSummary[]>(MEASUREMENT_RUNS);
  const [importedFiles, setImportedFiles] = useState<ImportedFileRecord[]>([]);
  const [seriesAppends, setSeriesAppends] = useState<Record<string, MeasurementPoint[]>>({});

  const decideRecommendation = (
    id: string,
    state: RecommendationState,
    decidedBy: string,
    comment: string
  ) => {
    setRecommendations((prev) =>
      prev.map((rec) =>
        rec.id === id
          ? { ...rec, state, decidedBy, decidedAt: new Date().toISOString(), decisionComment: comment }
          : rec
      )
    );
  };

  const addActionTaken = (
    recommendationId: string,
    input: { description: string; outcomeStatus: ActionOutcomeStatus }
  ) => {
    setRecommendations((prev) =>
      prev.map((rec) =>
        rec.id === recommendationId
          ? {
              ...rec,
              actionsTaken: [
                ...rec.actionsTaken,
                {
                  id: `action-${recommendationId}-${rec.actionsTaken.length + 1}`,
                  description: input.description,
                  outcomeStatus: input.outcomeStatus,
                  createdAt: new Date().toISOString(),
                },
              ],
            }
          : rec
      )
    );
  };

  const getSeries = (characteristicId: string): MeasurementPoint[] => {
    const base = getSeriesForCharacteristic(characteristicId);
    const extra = seriesAppends[characteristicId];
    return extra && extra.length > 0 ? [...base, ...extra] : base;
  };

  const importFile = (scenarioId: string): string => {
    const scenario = IMPORT_SCENARIOS.find((s) => s.id === scenarioId);
    if (!scenario) throw new Error(`Unknown import scenario: ${scenarioId}`);

    const recordId = `import-${scenarioId}-${Date.now()}`;
    const record: ImportedFileRecord = {
      id: recordId,
      scenarioId,
      filename: scenario.filename,
      partId: scenario.partId,
      status: "parsing",
      uploadedAt: new Date().toISOString(),
      sha256: fakeSha256(scenario.id + Date.now()),
    };
    setImportedFiles((prev) => [record, ...prev]);

    window.setTimeout(() => {
      if (scenario.willQuarantine || !scenario.partId) {
        setImportedFiles((prev) =>
          prev.map((f) =>
            f.id === recordId ? { ...f, status: "quarantined", errorDetail: scenario.quarantineReason } : f
          )
        );
        return;
      }

      const partId = scenario.partId;
      const affected = CHARACTERISTICS.filter((c) => c.partId === partId);
      const now = new Date();
      setSeriesAppends((prev) => {
        const next = { ...prev };
        affected.forEach((c, i) => {
          const existing = [...getSeriesForCharacteristic(c.id), ...(prev[c.id] ?? [])];
          const newPoints = simulateNewPoints(
            c.specification,
            existing,
            scenario.sampleCount,
            now,
            c.balloonNumber.length * 97 + i + Date.now() % 1000
          );
          next[c.id] = [...(prev[c.id] ?? []), ...newPoints];
        });
        return next;
      });

      const runId = `run-${scenarioId}-${Date.now()}`;
      setMeasurementRuns((prev) => [
        {
          id: runId,
          partId,
          machineCode: PARTS.findIndex((p) => p.id === partId) === 2 ? "SCAN-01" : "CMM-01",
          startedAt: now.toISOString(),
          sampleCount: scenario.sampleCount,
          nokCount: 0,
        },
        ...prev,
      ]);

      setImportedFiles((prev) => prev.map((f) => (f.id === recordId ? { ...f, status: "parsed", runId } : f)));
    }, 1200);

    return recordId;
  };

  const value = useMemo<DemoDataContextValue>(
    () => ({
      parts: PARTS,
      characteristics: CHARACTERISTICS,
      riskAssessments: RISK_ASSESSMENTS,
      recommendations,
      processEvents: PROCESS_EVENTS,
      measurementRuns,
      importScenarios: IMPORT_SCENARIOS,
      importedFiles,
      getSeries,
      decideRecommendation,
      addActionTaken,
      importFile,
    }),
    [recommendations, measurementRuns, importedFiles, seriesAppends]
  );

  return <DemoDataContext.Provider value={value}>{children}</DemoDataContext.Provider>;
}

export function useDemoData(): DemoDataContextValue {
  const ctx = useContext(DemoDataContext);
  if (!ctx) throw new Error("useDemoData must be used within DemoDataProvider");
  return ctx;
}
