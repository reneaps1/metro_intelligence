import type { DataOrigin } from "./origin";

// IQ-F1: the commercial walkthrough, trimmed to piece characteristics
// (2026-11-12): quality and a piece-only predictive step. The context, IIoT
// lab, process-quality and real-integration steps keep their components in
// steps/ but are out of the walkthrough. Route paths are
// generic on purpose -- the customer name never appears in a URL.
export const DEMO_BASE_PATH = "/demo/industrial-quality";
/** IQ-F15: full-screen line quality panel, outside the walkthrough steps. */
export const LINE_PANEL_PATH = `${DEMO_BASE_PATH}/panel-linea`;

/** Groups of the project tree (design-system.md §4.1). */
export type DemoStepGroup = "Calidad" | "Predictivo";

export interface DemoStep {
  id: string;
  number: number;
  title: string;
  /** Label for the project tree, where the full title would truncate. */
  short: string;
  group: DemoStepGroup;
  summary: string;
  origins: DataOrigin[];
  /** The step shows the simulated process scenario (and its alarms). */
  usesScenario?: boolean;
}

export const DEMO_STEPS: DemoStep[] = [
  {
    id: "quality",
    number: 1,
    title: "Diagnóstico de calidad",
    short: "Diagnóstico",
    group: "Calidad",
    summary: "KPIs, tendencia de NOK, Pareto y el nido crítico.",
    origins: ["SIMULATED", "PRECOMPUTED"],
  },
  {
    id: "dimensional",
    number: 2,
    title: "Exploración dimensional",
    short: "Dimensional",
    group: "Calidad",
    summary: "Variables, distribución, tolerancias y control estadístico por nido, turno y máquina.",
    origins: ["SIMULATED"],
  },
  {
    id: "ai",
    number: 3,
    title: "IA predictiva y oleadas NOK",
    short: "IA predictiva",
    group: "Predictivo",
    summary:
      "Resultados ML/DL históricos, oleadas NOK, CUSUM y riesgo por pieza a partir de las características medidas.",
    origins: ["PRECOMPUTED", "SIMULATED", "EXPERIMENTAL"],
  },
];

export function stepPath(step: DemoStep): string {
  return `${DEMO_BASE_PATH}/${step.id}`;
}
