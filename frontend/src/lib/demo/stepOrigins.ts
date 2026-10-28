import { DEMO_DATASET_ID, isRealDatasetId } from "../quality-analytics/filters";
import type { DataOrigin } from "./origin";
import type { DemoStep } from "./steps";

// IQ-F6: steps 2/3 analysing an imported CSV show a closed-period file, not
// the simulated dataset (the precomputed private report is hidden there too).
// IQ-F10: the customer's REAL dataset is computed here over real data; step 2
// also shows the private precomputed report.
// IQ-F12: step 6 adds REAL when its lab runs on the customer's REAL dataset
// (what-if and machine failures stay simulated, so SIMULATED remains).
// IQ-F13: step 5 adds REAL when the REAL dataset is the active one (Vista A
// joins its pieces with simulated signals; Vista B stays all simulated).
export function stepOrigins(step: DemoStep, datasetId: string, aiDatasetId: string | null = null): DataOrigin[] {
  if (step.id === "ai" && aiDatasetId && isRealDatasetId(aiDatasetId)) return ["REAL", ...step.origins];
  if (step.id === "correlation" && isRealDatasetId(datasetId)) return ["REAL", ...step.origins];
  const dimensional = step.id === "quality" || step.id === "dimensional";
  if (!dimensional) return step.origins;
  if (isRealDatasetId(datasetId)) return step.id === "quality" ? ["REAL", "PRECOMPUTED"] : ["REAL"];
  return datasetId !== DEMO_DATASET_ID ? ["HISTORICAL"] : step.origins;
}
