import { DEMO_DATASET_ID } from "../quality-analytics/filters";
import type { DataOrigin } from "./origin";
import type { DemoStep } from "./steps";

// IQ-F6: steps 2/3 analysing an imported CSV show a closed-period file, not
// the simulated dataset (the precomputed private report is hidden there too).
export function stepOrigins(step: DemoStep, datasetId: string): DataOrigin[] {
  const dimensional = step.id === "quality" || step.id === "dimensional";
  return dimensional && datasetId !== DEMO_DATASET_ID ? ["HISTORICAL"] : step.origins;
}
