import type { DataOrigin } from "./origin";

// IQ-F1: the 7-step commercial walkthrough. Route paths are generic on
// purpose -- the customer name never appears in a URL.
export const DEMO_BASE_PATH = "/demo/industrial-quality";

export interface DemoStep {
  id: string;
  number: number;
  title: string;
  summary: string;
  origins: DataOrigin[];
}

export const DEMO_STEPS: DemoStep[] = [
  {
    id: "context",
    number: 1,
    title: "Contexto industrial",
    summary: "Del disparo de inyección al veredicto OK/NOK, y qué fuentes de datos hay detrás.",
    origins: ["HISTORICAL", "SIMULATED", "PRECOMPUTED"],
  },
  {
    id: "quality",
    number: 2,
    title: "Diagnóstico de calidad",
    summary: "KPIs, tendencia de NOK, Pareto y el nido crítico.",
    origins: ["HISTORICAL", "PRECOMPUTED"],
  },
  {
    id: "dimensional",
    number: 3,
    title: "Exploración dimensional",
    summary: "Variables, distribución, tolerancias y control estadístico por nido, turno y máquina.",
    origins: ["HISTORICAL", "REAL"],
  },
  {
    id: "iiot",
    number: 4,
    title: "Laboratorio IIoT",
    summary: "Árbol de señales de máquina, curvas superpuestas, eventos y reproducción.",
    origins: ["SIMULATED"],
  },
  {
    id: "correlation",
    number: 5,
    title: "Relación proceso–calidad",
    summary: "Dispersión, correlación y regresión con desfase temporal; hipótesis, no causalidad.",
    origins: ["SIMULATED", "EXPERIMENTAL"],
  },
  {
    id: "ai",
    number: 6,
    title: "IA predictiva y oleadas NOK",
    summary: "Resultados ML/DL históricos, falsas alarmas y detección experimental de oleadas.",
    origins: ["PRECOMPUTED", "EXPERIMENTAL"],
  },
  {
    id: "integration",
    number: 7,
    title: "Integración real",
    summary: "Qué haría falta para validar causalidad y predicción en planta.",
    origins: [],
  },
];

export function stepPath(step: DemoStep): string {
  return `${DEMO_BASE_PATH}/${step.id}`;
}
