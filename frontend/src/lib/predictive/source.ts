import { DEMO_DATASET_ID } from "../quality-analytics/filters";
import type { QualityDataset } from "../quality-analytics/types";

// IQ-F12: which dataset the predictive-lab panels analyse. The synthetic demo
// dataset by default; the customer's REAL dataset when it is configured
// locally and selected. Panels that never depend on it (model lab, what-if,
// machine failures) ignore it.

export interface PredictiveSource {
  datasetId: string;
  /** The REAL dataset when selected; null = synthetic demo dataset. */
  real: QualityDataset | null;
}

export const SYNTHETIC_SOURCE: PredictiveSource = { datasetId: DEMO_DATASET_ID, real: null };

/** NOK targets of a REAL dataset: the total verdict or one station (first failing). */
export function targetOptions(real: QualityDataset): { value: string; label: string }[] {
  return [
    { value: "total", label: "Resultado total de la máquina" },
    ...(real.stations ?? []).map((s) => ({ value: `station:${s.key}`, label: `Primera falla: ${s.name}` })),
  ];
}

/** "dd mmm hh:mm" in plant local time (offset in minutes; 0 = UTC). */
export function plantLabel(ts: number, offsetMinutes = 0, withTime = true): string {
  return new Date((ts + offsetMinutes * 60) * 1000).toLocaleString("es-MX", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}
