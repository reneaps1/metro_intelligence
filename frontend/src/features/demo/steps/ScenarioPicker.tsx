import clsx from "clsx";
import { Card, CardHeader } from "../../../components/ui/Card";
import type { AsyncState } from "../../../lib/catalog/hooks";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import type { ScenarioListResponse } from "../../../lib/industrial-signals/types";

// IQ-F3/F4: shared selector for the simulated process scenario (demo session state).
export function ScenarioPicker({ scenarios }: { scenarios: AsyncState<ScenarioListResponse> }) {
  const { scenarioId, setScenarioId } = useDemoSession();
  return (
    <Card>
      <CardHeader title="Escenario de proceso" />
      {scenarios.loading && <p className="text-sm text-text-secondary">Cargando escenarios…</p>}
      {scenarios.error && (
        <p role="alert" className="text-sm text-status-nok">
          {scenarios.error}
        </p>
      )}
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {scenarios.data?.items.map((scenario) => (
          <button
            key={scenario.id}
            type="button"
            aria-pressed={scenario.id === scenarioId}
            onClick={() => setScenarioId(scenario.id)}
            className={clsx(
              "rounded border p-3 text-left transition-colors",
              scenario.id === scenarioId
                ? "border-brand-primary bg-surface-app"
                : "border-border bg-surface hover:border-brand-primary",
            )}
          >
            <span className="block text-sm font-semibold text-text-primary">{scenario.name}</span>
            <span className="block text-xs text-text-secondary">{scenario.description}</span>
            <span className="mt-1 block text-xs text-text-secondary">{scenario.event_count} eventos anotados</span>
          </button>
        ))}
      </div>
    </Card>
  );
}
