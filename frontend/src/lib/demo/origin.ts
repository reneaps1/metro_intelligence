// IQ-F1: every demo panel declares where its numbers come from, so real,
// simulated, precomputed and experimental content can never be confused.
export type DataOrigin = "REAL" | "HISTORICAL" | "SIMULATED" | "PRECOMPUTED" | "EXPERIMENTAL";

export const DATA_ORIGINS: DataOrigin[] = ["REAL", "HISTORICAL", "SIMULATED", "PRECOMPUTED", "EXPERIMENTAL"];

export const ORIGIN_INFO: Record<DataOrigin, { label: string; description: string }> = {
  REAL: {
    label: "Real",
    description: "Calculado en la plataforma sobre un archivo importado y autorizado.",
  },
  HISTORICAL: {
    label: "Histórico",
    description: "Datos dimensionales de un período cerrado; no es telemetría en vivo.",
  },
  SIMULATED: {
    label: "Simulado",
    description: "Generado por el simulador de proceso; no fue medido en planta.",
  },
  PRECOMPUTED: {
    label: "Precalculado",
    description: "Cifra de una evaluación histórica previa, no una inferencia en línea.",
  },
  EXPERIMENTAL: {
    label: "Experimental",
    description: "Modelo o regla sin validar para control productivo.",
  },
};
