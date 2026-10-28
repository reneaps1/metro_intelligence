import { DEMO_DATASET_ID, isRealDatasetId } from "../quality-analytics/filters";
import type { DataOrigin } from "./origin";
import type { DemoStep } from "./steps";

// IQ-F6: steps 2/3 analysing an imported CSV show a closed-period file, not
// the simulated dataset (the precomputed private report is hidden there too).
// IQ-F10: the customer's REAL dataset is computed here over real data; step 2
// also shows the private precomputed report.
export function stepOrigins(step: DemoStep, datasetId: string): DataOrigin[] {
  const dimensional = step.id === "quality" || step.id === "dimensional";
  if (!dimensional) return step.origins;
  if (isRealDatasetId(datasetId)) return step.id === "quality" ? ["REAL", "PRECOMPUTED"] : ["REAL"];
  return datasetId !== DEMO_DATASET_ID ? ["HISTORICAL"] : step.origins;
}
