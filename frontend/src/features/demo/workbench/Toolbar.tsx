import { ChevronLeft, ChevronRight, PanelLeft, PanelRight } from "lucide-react";
import clsx from "clsx";
import { Key } from "../../../components/workbench/Key";
import { PartControl } from "./PartControl";

// Toolbar of the demo workbench: the single home of location and the
// walkthrough position (design-system.md §4.1). The simulated-scenario and
// alarm controls left with the process steps (2026-11-12).

const iconButton =
  "flex h-[34px] w-[34px] items-center justify-center rounded-md text-text-primary hover:bg-wb-pane-header";

interface ToolbarProps {
  treeVisible: boolean;
  onToggleTree: () => void;
  inspectorVisible: boolean;
  onToggleInspector: () => void;
  crumbs: string[];
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
      <PartControl />
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
