import { Card } from "../../../components/ui/Card";
import type { AsyncState } from "../../../lib/catalog/hooks";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import type { ScenarioListResponse } from "../../../lib/industrial-signals/types";

// IQ-F3/F4: the simulated process scenario these steps show. Read-only: the
// workbench toolbar is the single place to change it (design-system.md §4.1).
export function ScenarioSummary({ scenarios }: { scenarios: AsyncState<ScenarioListResponse> }) {
  const { scenarioId } = useDemoSession();
  const scenario = scenarios.data?.items.find((s) => s.id === scenarioId);
  return (
    <Card>
      <div aria-label="Escenario de proceso" className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm">
        <span className="text-text-secondary">Escenario de proceso</span>
        {scenarios.loading && <span className="text-text-secondary">Cargando escenarios…</span>}
        {scenarios.error && (
          <span role="alert" className="text-status-nok">
            {scenarios.error}
          </span>
        )}
        {scenario && (
          <>
            <span className="font-semibold text-text-primary">{scenario.name}</span>
            <span className="text-text-secondary">
              {scenario.description} · {scenario.event_count}{" "}
              {scenario.event_count === 1 ? "evento anotado" : "eventos anotados"}
            </span>
            <span className="text-xs text-text-secondary">Cámbialo desde «Escenario» en la barra de herramientas.</span>
          </>
        )}
      </div>
    </Card>
  );
}
