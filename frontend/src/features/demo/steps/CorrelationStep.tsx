import { useAsync } from "../../../lib/catalog/hooks";
import { fetchScenarios } from "../../../lib/industrial-signals/api";
import { CorrelationPanel } from "../../industrial-analytics/CorrelationPanel";
import { ScenarioSummary } from "./ScenarioPicker";

// IQ-F4/F13: demo step 5 -- process/quality relationship: Vista B (all synthetic) and
// Vista A (REAL pieces + simulated signals on the real calendar, local only).
export function CorrelationStep() {
  const scenarios = useAsync(fetchScenarios, []);
  return (
    <div className="space-y-4">
      <ScenarioSummary scenarios={scenarios} />
      <CorrelationPanel />
    </div>
  );
}
