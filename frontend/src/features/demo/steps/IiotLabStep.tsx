import { AudioWaveform } from "lucide-react";
import { useAsync } from "../../../lib/catalog/hooks";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { fetchScenarios } from "../../../lib/industrial-signals/api";
import { SignalExplorer } from "../../industrial-analytics/SignalExplorer";
import { ScenarioSummary } from "./ScenarioPicker";

// IQ-F3: demo step 4 -- the active scenario + the interactive signal explorer.
export function IiotLabStep() {
  const { scenarioId } = useDemoSession();
  const scenarios = useAsync(fetchScenarios, []);
  const scenario = scenarios.data?.items.find((s) => s.id === scenarioId) ?? null;

  return (
    <div className="space-y-4">
      <p className="flex items-start gap-2 border-l-4 border-border bg-surface px-3 py-2 text-sm text-text-secondary">
        <AudioWaveform size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        Señales simuladas por un generador determinista: no fueron medidas en ninguna planta ni representan
        especificaciones de máquinas reales.
      </p>
      <ScenarioSummary scenarios={scenarios} />
      {scenario && <SignalExplorer key={scenario.id} scenario={scenario} />}
    </div>
  );
}
