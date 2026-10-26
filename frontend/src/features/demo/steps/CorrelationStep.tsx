import { useAsync } from "../../../lib/catalog/hooks";
import { fetchScenarios } from "../../../lib/industrial-signals/api";
import { CorrelationPanel } from "../../industrial-analytics/CorrelationPanel";
import { ScenarioPicker } from "./ScenarioPicker";

// IQ-F4: demo step 5 -- process/quality relationship (Vista B today, Vista A after F5/F6).
export function CorrelationStep() {
  const scenarios = useAsync(fetchScenarios, []);
  return (
    <div className="space-y-4">
      <ScenarioPicker scenarios={scenarios} />
      <CorrelationPanel />
    </div>
  );
}
