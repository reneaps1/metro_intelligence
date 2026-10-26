import { Cpu } from "lucide-react";
import clsx from "clsx";
import { Card, CardHeader } from "../../../components/ui/Card";
import { StatusChip, type ChipStatus } from "../../../components/ui/StatusChip";
import { useAsync } from "../../../lib/catalog/hooks";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { collectSignals, fetchProcessEvents, fetchScenarios, fetchSignalTree } from "../../../lib/industrial-signals/api";
import type { ProcessEventSeverity, SignalTreeNode } from "../../../lib/industrial-signals/types";

// IQ-F2: first view over the real (simulated-data) industrial-signals API:
// scenario selection, the machine/signal inventory and annotated events.
// The interactive multi-trace explorer replaces the inventory in F3.

const SEVERITY_CHIP: Record<ProcessEventSeverity, ChipStatus> = {
  info: "info",
  warning: "warning",
  critical: "critical",
};

const SEVERITY_LABEL: Record<ProcessEventSeverity, string> = {
  info: "Info",
  warning: "Aviso",
  critical: "Crítico",
};

/** Offset from the scenario start as "T+hh:mm". */
export function formatOffset(fromIso: string, toIso: string): string {
  const minutes = Math.max(0, Math.floor((Date.parse(toIso) - Date.parse(fromIso)) / 60000));
  const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mm = String(minutes % 60).padStart(2, "0");
  return `T+${hh}:${mm}`;
}

function machines(root: SignalTreeNode): SignalTreeNode[] {
  if (root.node_type === "machine") return [root];
  return root.children.flatMap(machines);
}

export function IiotSourcesStep() {
  const { scenarioId, setScenarioId } = useDemoSession();
  const scenarios = useAsync(fetchScenarios, []);
  const tree = useAsync(fetchSignalTree, []);
  const events = useAsync(() => fetchProcessEvents(scenarioId), [scenarioId]);

  const selected = scenarios.data?.items.find((s) => s.id === scenarioId) ?? null;
  const error = scenarios.error ?? tree.error;

  return (
    <div className="space-y-4">
      <p className="flex items-start gap-2 rounded bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
        <Cpu size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
        Señales simuladas por un generador determinista: no fueron medidas en ninguna planta ni representan
        especificaciones de máquinas reales.
      </p>

      {error && (
        <p role="alert" className="text-sm text-status-nok">
          {error}
        </p>
      )}

      <Card>
        <CardHeader title="Escenario de proceso" />
        {scenarios.loading && <p className="text-sm text-text-secondary">Cargando escenarios…</p>}
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

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Inventario de señales" />
          {tree.loading && <p className="text-sm text-text-secondary">Cargando árbol de señales…</p>}
          {tree.data &&
            machines(tree.data.root).map((machine) => {
              const signals = collectSignals(machine);
              const digital = signals.filter((s) => s.signal?.value_type === "digital").length;
              return (
                <div key={machine.id} className="mb-3 last:mb-0">
                  <p className="text-sm font-semibold text-text-primary">
                    {machine.name}{" "}
                    <span className="font-normal text-text-secondary">
                      · {signals.length} señales ({signals.length - digital} analógicas/discretas, {digital} digitales)
                    </span>
                  </p>
                  <ul className="mt-1 flex flex-wrap gap-1">
                    {machine.children.map((group) => (
                      <li key={group.id} className="rounded bg-surface-app px-2 py-0.5 text-xs text-text-secondary">
                        {group.name} ({group.children.length})
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          <p className="mt-3 text-xs text-text-secondary">
            Próxima fase (F3): explorador interactivo con arrastrar señales, ejes por unidad, zoom y cursores A/B.
          </p>
        </Card>

        <Card>
          <CardHeader title={selected ? `Eventos: ${selected.name}` : "Eventos del escenario"} />
          {events.loading && <p className="text-sm text-text-secondary">Cargando eventos…</p>}
          {events.error && <p className="text-sm text-status-nok">{events.error}</p>}
          {events.data && selected && (
            <ol className="space-y-2" aria-label="Eventos del escenario">
              {events.data.items.map((event) => (
                <li key={event.id} className="flex items-start gap-3 text-sm">
                  <span className="w-16 shrink-0 font-mono text-xs text-text-secondary">
                    {formatOffset(selected.start, event.start)}
                  </span>
                  <span className="flex-1 text-text-primary">{event.label}</span>
                  <StatusChip status={SEVERITY_CHIP[event.severity]} label={SEVERITY_LABEL[event.severity]} />
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </div>
  );
}
