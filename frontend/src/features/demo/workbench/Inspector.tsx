import { Fragment, type ReactNode } from "react";
import { OriginBadge } from "../../../components/ui/OriginBadge";
import { ORIGIN_INFO, type DataOrigin } from "../../../lib/demo/origin";

// Inspector of the demo workbench: technical details of the open view --
// provenance with its meaning, the simulated scenario behind it and the
// session context. It replaces the former properties pane and output log; the
// last action now lives in the status bar.

export interface InspectorRow {
  label: string;
  value: ReactNode;
  mono?: boolean;
}

export interface InspectorSection {
  title: string;
  rows: InspectorRow[];
}

export function Inspector({ origins, sections }: { origins: DataOrigin[]; sections: InspectorSection[] }) {
  return (
    <aside
      aria-label="Inspector"
      className="hidden w-[288px] flex-none flex-col overflow-y-auto border-l border-border bg-surface text-[13px] xl:flex"
    >
      <h2 className="border-b border-border px-3.5 py-2.5 text-xs font-semibold text-text-secondary">
        Detalles técnicos de la vista
      </h2>
      <section aria-label="Procedencia" className="border-b border-border px-3.5 py-3">
        <h3 className="mb-2 text-[13px] font-semibold">Procedencia</h3>
        {origins.length === 0 ? (
          <p className="text-text-secondary">Sin datos medidos ni simulados: es un paso de contexto.</p>
        ) : (
          <ul className="space-y-2.5">
            {origins.map((origin) => (
              <li key={origin} className="space-y-1">
                <OriginBadge origin={origin} />
                <p className="text-text-secondary">{ORIGIN_INFO[origin].description}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
      {sections.map((section) => (
        <section key={section.title} aria-label={section.title} className="border-b border-border px-3.5 py-3">
          <h3 className="mb-1 text-[13px] font-semibold">{section.title}</h3>
          <dl className="grid grid-cols-[auto_minmax(0,1fr)]">
            {section.rows.map((row) => (
              <Fragment key={row.label}>
                <dt className="border-b border-border py-1.5 pr-3 text-text-secondary">{row.label}</dt>
                <dd className={`break-words border-b border-border py-1.5 ${row.mono ? "font-mono" : ""}`}>
                  {row.value}
                </dd>
              </Fragment>
            ))}
          </dl>
        </section>
      ))}
    </aside>
  );
}
