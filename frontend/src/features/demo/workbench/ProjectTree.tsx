import { Link, NavLink } from "react-router-dom";
import { MonitorDot } from "lucide-react";
import clsx from "clsx";
import { DEMO_BASE_PATH, DEMO_STEPS, LINE_PANEL_PATH, stepPath, type DemoStep } from "../../../lib/demo/steps";

// Project tree of the demo workbench: two levels (group › step), the HIG
// sidebar maximum, plus the plant screens (line quality panel). The asset
// list left with the process steps (2026-11-12).

const row = (active: boolean) =>
  clsx(
    "flex min-h-[32px] items-center gap-2 rounded-sm px-2 text-[13px]",
    active ? "bg-wb-selected font-semibold text-text-primary shadow-[inset_3px_0_0_var(--brand-accent)]" : "text-text-primary hover:bg-wb-pane-header",
  );

function groupSteps(): { group: string; steps: DemoStep[] }[] {
  const groups: { group: string; steps: DemoStep[] }[] = [];
  for (const step of DEMO_STEPS) {
    const last = groups[groups.length - 1];
    if (last?.group === step.group) last.steps.push(step);
    else groups.push({ group: step.group, steps: [step] });
  }
  return groups;
}

export function ProjectTree({ isHome }: { isHome: boolean }) {
  return (
    <aside
      aria-label="Árbol del proyecto"
      className="hidden w-[232px] flex-none flex-col overflow-y-auto border-r border-border bg-surface lg:flex"
    >
      <div className="px-1.5 pt-2">
        <Link to={DEMO_BASE_PATH} aria-current={isHome ? "page" : undefined} className={row(isHome)}>
          <span className="w-3.5" aria-hidden="true" />
          Inicio de la demo
        </Link>
      </div>
      <nav aria-label="Pasos de la demo" className="px-1.5">
        {groupSteps().map(({ group, steps }) => (
          <div key={group} className="pt-2.5">
            <h2 className="wb-label px-2 pb-1 !text-[11px]">{group}</h2>
            <ol>
              {steps.map((step) => (
                <li key={step.id}>
                  <NavLink
                    to={stepPath(step)}
                    title={`Paso ${step.number}: ${step.title}`}
                    className={({ isActive }) => row(isActive)}
                  >
                    <span className="w-3.5 text-right font-mono text-xs text-text-secondary">{step.number}</span>
                    <span className="min-w-0 flex-1 truncate">{step.short}</span>
                  </NavLink>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </nav>
      <div className="mt-3 border-t border-border px-1.5 py-2.5">
        <h2 className="wb-label px-2 pb-1 !text-[11px]">Pantallas de planta</h2>
        <Link to={LINE_PANEL_PATH} title="Pantalla completa para la línea" className={row(false)}>
          <MonitorDot size={14} className="text-text-secondary" aria-hidden="true" />
          <span className="min-w-0 flex-1 truncate">Panel de calidad en línea</span>
        </Link>
      </div>
    </aside>
  );
}
