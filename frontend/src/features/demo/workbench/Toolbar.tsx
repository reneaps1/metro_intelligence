import { useCallback, useEffect, useState } from "react";
import { AudioWaveform, Bell, ChevronDown, ChevronLeft, ChevronRight, PanelLeft, PanelRight } from "lucide-react";
import clsx from "clsx";
import type { Scenario } from "../../../lib/industrial-signals/types";
import type { SimulatedAlarm } from "../../../lib/demo/alarms";
import { topPriority } from "../../../lib/demo/alarms";
import { Key } from "../../../components/workbench/Key";
import { AlarmIcon } from "./AlarmIcon";
import { usePopover } from "./usePopover";

// Toolbar of the demo workbench: the single home of location, scenario,
// alarms and the walkthrough position (design-system.md §4.1). Navigation
// controls are outlined; process-like actions (Aplicar, Reconocer) are solid,
// so the two never look alike (ISA-101).

const iconButton =
  "flex h-[34px] w-[34px] items-center justify-center rounded-md text-text-primary hover:bg-wb-pane-header";

export type ToolbarPopover = "scenario" | "alarms" | null;

interface ToolbarProps {
  treeVisible: boolean;
  onToggleTree: () => void;
  inspectorVisible: boolean;
  onToggleInspector: () => void;
  crumbs: string[];
  popover: ToolbarPopover;
  onPopover: (popover: ToolbarPopover) => void;
  scenarios: Scenario[];
  scenarioId: string;
  onApplyScenario: (id: string) => void;
  onResetScenario: () => void;
  alarms: (SimulatedAlarm & { acknowledged: boolean })[];
  onAcknowledgeAll: () => void;
  onShowAlarmSignal: () => void;
  position: string;
  atStart: boolean;
  prevLabel: string;
  nextLabel: string;
  onPrev: () => void;
  onNext: () => void;
}

export function Toolbar(props: ToolbarProps) {
  const { crumbs } = props;
  return (
    <div className="flex min-h-[48px] flex-none flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-border bg-wb-pane-header px-3 py-1.5">
      <button
        type="button"
        onClick={props.onToggleTree}
        aria-pressed={props.treeVisible}
        aria-label="Árbol del proyecto"
        title="Mostrar u ocultar el árbol del proyecto"
        className={clsx(iconButton, "hidden lg:flex", props.treeVisible && "bg-wb-selected")}
      >
        <PanelLeft size={18} aria-hidden="true" />
      </button>
      <nav aria-label="Ruta" className="flex min-w-0 items-center gap-1.5 text-sm">
        {crumbs.map((crumb, i) => {
          const last = i === crumbs.length - 1;
          return (
            <span key={crumb} className="flex min-w-0 items-center gap-1.5">
              {i > 0 && (
                <span aria-hidden="true" className="text-text-secondary">
                  ›
                </span>
              )}
              <span
                aria-current={last ? "page" : undefined}
                className={clsx("truncate", last ? "font-semibold text-text-primary" : "text-text-secondary")}
              >
                {crumb}
              </span>
            </span>
          );
        })}
      </nav>
      <span className="flex-1" />
      <ScenarioControl {...props} />
      <AlarmsControl {...props} />
      <div role="group" aria-label="Recorrido" className="flex items-center gap-0.5 rounded-md border border-border bg-surface px-1">
        <span className="hidden pl-1 2xl:inline-grid">
          <Key>Re Pág</Key>
        </span>
        <button
          type="button"
          onClick={props.onPrev}
          disabled={props.atStart}
          aria-label={props.prevLabel}
          title={`${props.prevLabel} · Re Pág`}
          className={clsx(iconButton, "disabled:opacity-40 disabled:hover:bg-transparent")}
        >
          <ChevronLeft size={16} strokeWidth={2.5} aria-hidden="true" />
        </button>
        <span className="min-w-[56px] text-center font-mono text-[13px] font-semibold">{props.position}</span>
        <button
          type="button"
          onClick={props.onNext}
          aria-label={props.nextLabel}
          title={`${props.nextLabel} · Av Pág`}
          className={iconButton}
        >
          <ChevronRight size={16} strokeWidth={2.5} aria-hidden="true" />
        </button>
        <span className="hidden pr-1 2xl:inline-grid">
          <Key>Av Pág</Key>
        </span>
      </div>
      <button
        type="button"
        onClick={props.onToggleInspector}
        aria-pressed={props.inspectorVisible}
        aria-label="Inspector"
        title="Mostrar u ocultar el inspector"
        className={clsx(iconButton, "hidden xl:flex", props.inspectorVisible && "bg-wb-selected")}
      >
        <PanelRight size={18} aria-hidden="true" />
      </button>
    </div>
  );
}

function ScenarioControl(props: ToolbarProps) {
  const open = props.popover === "scenario";
  const close = useCallback(() => props.onPopover(null), [props]);
  const ref = usePopover(open, close);
  const [pending, setPending] = useState(props.scenarioId);
  useEffect(() => {
    if (open) setPending(props.scenarioId);
  }, [open, props.scenarioId]);

  const active = props.scenarios.find((s) => s.id === props.scenarioId);
  const abnormal = props.scenarioId !== "normal";
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => props.onPopover(open ? null : "scenario")}
        title="Escenario simulado: cambiar"
        className={clsx(
          "flex min-h-[36px] items-center gap-2 rounded-md border border-l-4 pl-2.5 pr-3 hover:bg-wb-pane-header",
          abnormal ? "border-status-warning bg-status-warning-bg" : "border-border",
        )}
      >
        {abnormal ? (
          <AlarmIcon priority={2} />
        ) : (
          <AudioWaveform size={16} className="text-text-secondary" aria-hidden="true" />
        )}
        <span className="text-xs text-text-secondary">Escenario</span>
        <span className={clsx("text-sm font-semibold", abnormal ? "text-status-warning" : "text-text-primary")}>
          {active?.name ?? props.scenarioId}
        </span>
        <ChevronDown size={14} strokeWidth={2.5} className="text-text-secondary" aria-hidden="true" />
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Escenario simulado"
          className="absolute right-0 top-full z-dropdown mt-1 w-[380px] max-w-[92vw] rounded-md border border-border bg-surface-raised p-3 shadow-md"
        >
          <p className="mb-2 text-[13px] text-text-secondary">
            Afecta a Laboratorio IIoT y Relación proceso–calidad. Elige y aplica; no modifica datos guardados.
          </p>
          <div role="radiogroup" aria-label="Escenario simulado" className="flex flex-col gap-1">
            {props.scenarios.map((scenario) => {
              const checked = scenario.id === pending;
              return (
                <button
                  key={scenario.id}
                  type="button"
                  role="radio"
                  aria-checked={checked}
                  onClick={() => setPending(scenario.id)}
                  className={clsx(
                    "flex min-h-[44px] items-start gap-2.5 rounded-md border px-2.5 py-1.5 text-left",
                    checked ? "border-brand-primary bg-wb-selected" : "border-border hover:bg-wb-pane-header",
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={clsx(
                      "mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded-full border-2",
                      checked ? "border-brand-primary" : "border-border",
                    )}
                  >
                    {checked && <span className="h-1.5 w-1.5 rounded-full bg-brand-primary" />}
                  </span>
                  <span className="flex-1">
                    <span className="block text-sm font-medium text-text-primary">{scenario.name}</span>
                    <span className="block text-xs text-text-secondary">
                      {scenario.description} · {scenario.event_count}{" "}
                      {scenario.event_count === 1 ? "evento anotado" : "eventos anotados"}
                    </span>
                  </span>
                  {scenario.id === props.scenarioId && <span className="text-xs text-text-secondary">activo</span>}
                </button>
              );
            })}
          </div>
          <div className="mt-2.5 flex gap-1.5">
            <button
              type="button"
              disabled={pending === props.scenarioId}
              onClick={() => {
                props.onApplyScenario(pending);
                close();
              }}
              className="min-h-[38px] flex-1 rounded-md bg-brand-primary font-semibold text-text-on-brand disabled:opacity-40"
            >
              Aplicar escenario
            </button>
            <button
              type="button"
              onClick={() => {
                props.onResetScenario();
                close();
              }}
              className="min-h-[38px] rounded-md border border-border px-3 text-sm hover:bg-wb-pane-header"
            >
              Restaurar escenario demo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function AlarmsControl(props: ToolbarProps) {
  const open = props.popover === "alarms";
  const close = useCallback(() => props.onPopover(null), [props]);
  const ref = usePopover(open, close);
  const { alarms } = props;
  const top = topPriority(alarms);
  const unacknowledged = alarms.filter((a) => !a.acknowledged).length;
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`Alarmas: ${alarms.length} activas, ${unacknowledged} sin reconocer`}
        onClick={() => props.onPopover(open ? null : "alarms")}
        className="flex min-h-[36px] items-center gap-2 rounded-md border border-border px-3 hover:bg-wb-pane-header"
      >
        {top ? (
          <AlarmIcon priority={top} blinking={unacknowledged > 0} />
        ) : (
          <Bell size={16} className="text-text-secondary" aria-hidden="true" />
        )}
        <span className="text-sm">Alarmas</span>
        <span className="min-w-[22px] rounded-md bg-surface-app px-1.5 font-mono text-[13px] font-semibold">
          {alarms.length}
        </span>
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Resumen de alarmas"
          className="absolute right-0 top-full z-dropdown mt-1 w-[480px] max-w-[92vw] rounded-md border border-border bg-surface-raised shadow-md"
        >
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <h2 className="flex-1 text-[15px] font-semibold">Resumen de alarmas</h2>
            {unacknowledged > 0 && (
              <button
                type="button"
                onClick={props.onAcknowledgeAll}
                className="min-h-[32px] rounded-md bg-brand-primary px-3 text-sm font-semibold text-text-on-brand"
              >
                Reconocer todas
              </button>
            )}
          </div>
          {alarms.length === 0 ? (
            <p className="px-3 py-3.5 text-sm text-text-secondary">
              Sin alarmas activas. El escenario simulado actual no genera ninguna.
            </p>
          ) : (
            <ul>
              {alarms.map((alarm) => (
                <li
                  key={alarm.id}
                  className={clsx(
                    "flex items-center gap-2.5 border-b border-border px-3 py-2 last:border-b-0",
                    !alarm.acknowledged && (alarm.priority === 1 ? "bg-status-nok-bg" : "bg-status-warning-bg"),
                  )}
                >
                  <AlarmIcon priority={alarm.priority} blinking={!alarm.acknowledged} />
                  <span className="font-mono text-sm font-semibold">P{alarm.priority}</span>
                  <span className="flex min-w-0 flex-1 flex-col">
                    <span
                      className={clsx(
                        "text-sm font-semibold",
                        alarm.priority === 1 ? "text-status-nok" : "text-status-warning",
                      )}
                    >
                      {alarm.text}
                    </span>
                    <span className="text-xs text-text-secondary">
                      <span className="font-mono">{alarm.tag}</span> · {alarm.at} ·{" "}
                      {alarm.acknowledged ? "Reconocida" : "Sin reconocer"} · Simulada
                    </span>
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      props.onShowAlarmSignal();
                      close();
                    }}
                    className="text-sm text-brand-primary underline"
                  >
                    Ver señal
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
