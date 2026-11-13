import { AudioWaveform, Calculator, Database, FlaskConical, History } from "lucide-react";
import { ORIGIN_INFO, type DataOrigin } from "../../lib/demo/origin";

// Provenance is metadata, not status: every origin is neutral and told apart
// by icon and label, so the alarm colors stay reserved for alarms (ISA-101,
// design-system.md §1.3). Experimental keeps a dashed border as a second cue.
const STYLE: Record<DataOrigin, { icon: typeof Database; border: string }> = {
  REAL: { icon: Database, border: "border-solid" },
  HISTORICAL: { icon: History, border: "border-solid" },
  SIMULATED: { icon: AudioWaveform, border: "border-solid" },
  PRECOMPUTED: { icon: Calculator, border: "border-solid" },
  EXPERIMENTAL: { icon: FlaskConical, border: "border-dashed" },
};

export function OriginBadge({ origin }: { origin: DataOrigin }) {
  const { icon: Icon, border } = STYLE[origin];
  const { label, description } = ORIGIN_INFO[origin];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-sm border ${border} border-text-secondary px-1.5 py-0.5 text-xs font-semibold text-text-primary`}
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
