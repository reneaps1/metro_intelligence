import type { DataOrigin } from "./origin";

// IQ-F1: the 7-step commercial walkthrough. Route paths are generic on
// purpose -- the customer name never appears in a URL.
export const DEMO_BASE_PATH = "/demo/industrial-quality";
/** IQ-F15: full-screen line quality panel, outside the walkthrough steps. */
export const LINE_PANEL_PATH = `${DEMO_BASE_PATH}/panel-linea`;

/** Groups of the project tree (design-system.md §4.1). */
export type DemoStepGroup = "Recorrido" | "Calidad" | "Proceso" | "Predictivo" | "Planta";

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
    id: "context",
    number: 1,
    title: "Contexto industrial",
    short: "Contexto",
    group: "Recorrido",
    summary: "Del disparo de inyección al veredicto OK/NOK, y qué fuentes de datos hay detrás.",
    origins: ["HISTORICAL", "SIMULATED", "PRECOMPUTED"],
  },
  {
    id: "quality",
    number: 2,
    title: "Diagnóstico de calidad",
    short: "Diagnóstico",
    group: "Calidad",
    summary: "KPIs, tendencia de NOK, Pareto y el nido crítico.",
    origins: ["SIMULATED", "PRECOMPUTED"],
  },
  {
    id: "dimensional",
    number: 3,
    title: "Exploración dimensional",
    short: "Dimensional",
    group: "Calidad",
    summary: "Variables, distribución, tolerancias y control estadístico por nido, turno y máquina.",
    origins: ["SIMULATED"],
  },
  {
    id: "iiot",
    number: 4,
    title: "Laboratorio IIoT",
    short: "Laboratorio IIoT",
    group: "Proceso",
    summary: "Árbol de señales de máquina, curvas superpuestas, eventos y reproducción.",
    origins: ["SIMULATED"],
    usesScenario: true,
  },
  {
    id: "correlation",
    number: 5,
    title: "Relación proceso–calidad",
    short: "Proceso–calidad",
    group: "Proceso",
    summary: "Dispersión, correlación y regresión con desfase temporal; hipótesis, no causalidad.",
    origins: ["SIMULATED", "EXPERIMENTAL"],
    usesScenario: true,
  },
  {
    id: "ai",
    number: 6,
    title: "IA predictiva y oleadas NOK",
    short: "IA predictiva",
    group: "Predictivo",
    summary:
      "Resultados ML/DL históricos, falsas alarmas, oleadas NOK, CUSUM, what-if y predicción experimental de fallas.",
    origins: ["PRECOMPUTED", "SIMULATED", "EXPERIMENTAL"],
  },
  {
    id: "integration",
    number: 7,
    title: "Integración real",
    short: "Integración real",
    group: "Planta",
    summary: "Qué haría falta para validar causalidad y predicción en planta.",
    origins: [],
  },
];

export function stepPath(step: DemoStep): string {
  return `${DEMO_BASE_PATH}/${step.id}`;
}
