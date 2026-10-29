import { AudioWaveform } from "lucide-react";
import { Notice } from "../../../components/workbench/Notice";
import { useAsync } from "../../../lib/catalog/hooks";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { fetchScenarios } from "../../../lib/industrial-signals/api";
import { SignalExplorer } from "../../industrial-analytics/SignalExplorer";
import { ScenarioSummary } from "./ScenarioPicker";

// IQ-F3: demo step 4 -- the active scenario + the interactive signal explorer.
// IQ-F16: the provenance banner is a neutral workbench notice.
export function IiotLabStep() {
  const { scenarioId } = useDemoSession();
  const scenarios = useAsync(fetchScenarios, []);
  const scenario = scenarios.data?.items.find((s) => s.id === scenarioId) ?? null;

  return (
    <div className="space-y-4">
      <Notice icon={<AudioWaveform size={16} aria-hidden="true" />}>
        Señales simuladas por un generador determinista: no fueron medidas en ninguna planta ni representan
        especificaciones de máquinas reales.
      </Notice>
      <ScenarioSummary scenarios={scenarios} />
      {scenario && <SignalExplorer key={scenario.id} scenario={scenario} />}
    </div>
  );
}
