import { Calculator, Cpu, Database, FlaskConical, History } from "lucide-react";
import { ORIGIN_INFO, type DataOrigin } from "../../lib/demo/origin";

const STYLE: Record<DataOrigin, { icon: typeof Cpu; classes: string }> = {
  REAL: { icon: Database, classes: "bg-status-ok-bg text-status-ok" },
  HISTORICAL: { icon: History, classes: "bg-status-info-bg text-status-info" },
  SIMULATED: { icon: Cpu, classes: "bg-status-warning-bg text-status-warning" },
  PRECOMPUTED: { icon: Calculator, classes: "bg-status-neutral-bg text-status-neutral" },
  EXPERIMENTAL: { icon: FlaskConical, classes: "border border-dashed border-status-nok text-status-nok" },
};

export function OriginBadge({ origin }: { origin: DataOrigin }) {
  const { icon: Icon, classes } = STYLE[origin];
  const { label, description } = ORIGIN_INFO[origin];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${classes}`}
      title={description}
      data-origin={origin}
    >
      <Icon size={12} strokeWidth={2.5} aria-hidden="true" />
      {label}
    </span>
  );
}

export function OriginLegend({ origins }: { origins: DataOrigin[] }) {
  return (
    <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3" aria-label="Leyenda de procedencia de datos">
      {origins.map((origin) => (
        <li key={origin} className="flex items-start gap-2 text-sm text-text-secondary">
          <OriginBadge origin={origin} />
          <span>{ORIGIN_INFO[origin].description}</span>
        </li>
      ))}
    </ul>
  );
}
