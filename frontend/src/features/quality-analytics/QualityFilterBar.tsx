import type { ReactNode } from "react";
import { FilterX } from "lucide-react";
import clsx from "clsx";
import { Card } from "../../components/ui/Card";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import {
  DEFAULT_QUALITY_FILTERS,
  activeFilterCount,
  daysBetween,
  toggle,
  type QualityFilters,
} from "../../lib/quality-analytics/filters";
import type { QualityDataset } from "../../lib/quality-analytics/types";

// IQ-F5: coordinated filters for steps 2 and 3. Filters the dataset cannot
// support (missing metadata) are disabled with an explanation -- never faked.

const chip =
  "rounded border px-2 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40";

function Chip({ active, onClick, children, label }: { active: boolean; onClick: () => void; children: ReactNode; label?: string }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={label}
      onClick={onClick}
      className={clsx(
        chip,
        active ? "border-brand-primary bg-brand-primary text-text-on-brand" : "border-border bg-surface text-text-secondary hover:border-brand-primary",
      )}
    >
      {children}
    </button>
  );
}

function Group({ title, enabled, children }: { title: string; enabled: boolean; children: ReactNode }) {
  return (
    <fieldset className="min-w-0" disabled={!enabled}>
      <legend className="mb-1 text-xs font-semibold text-text-secondary">
        {title}
        {!enabled && <span className="ml-1 font-normal italic">(no disponible en este dataset)</span>}
      </legend>
      <div className="flex flex-wrap gap-1">{children}</div>
    </fieldset>
  );
}

export function QualityFilterBar({ dataset, showVariables = true }: { dataset: QualityDataset; showVariables?: boolean }) {
  const { qualityFilters: f, setQualityFilters } = useDemoSession();
  const set = (patch: Partial<QualityFilters>) => setQualityFilters((prev) => ({ ...prev, ...patch }));
  const days = daysBetween(dataset.period_start, dataset.period_end);
  const available = dataset.available_filters;
  const active = activeFilterCount(f);

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-end gap-4">
        <label className="text-xs font-semibold text-text-secondary">
          Desde
          <select
            className="ml-2 rounded border border-border bg-surface px-2 py-1 text-xs text-text-primary"
            value={f.startDay ?? ""}
            onChange={(e) => set({ startDay: e.target.value || null })}
            aria-label="Desde el día"
          >
            <option value="">Inicio</option>
            {days.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold text-text-secondary">
          Hasta
          <select
            className="ml-2 rounded border border-border bg-surface px-2 py-1 text-xs text-text-primary"
            value={f.endDay ?? ""}
            onChange={(e) => set({ endDay: e.target.value || null })}
            aria-label="Hasta el día"
          >
            <option value="">Fin</option>
            {days.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <Group title="Máquina" enabled={available.machine}>
          {dataset.machines.map((m) => (
            <Chip key={m} active={f.machines.includes(m)} onClick={() => set({ machines: toggle(f.machines, m) })}>
              {m}
            </Chip>
          ))}
        </Group>
        <Group title="Turno" enabled={available.shift}>
          {dataset.shifts.map((s) => (
            <Chip key={s} active={f.shifts.includes(s)} onClick={() => set({ shifts: toggle(f.shifts, s) })} label={`Turno ${s}`}>
              {s}
            </Chip>
          ))}
        </Group>
        <Group title="Lote" enabled={available.batch}>
          {dataset.batches.map((b) => (
            <Chip key={b} active={f.batches.includes(b)} onClick={() => set({ batches: toggle(f.batches, b) })}>
              {b}
            </Chip>
          ))}
        </Group>
        <button
          type="button"
          onClick={() => setQualityFilters((prev) => ({ ...DEFAULT_QUALITY_FILTERS, detailVariable: prev.detailVariable, groupBy: prev.groupBy }))}
          disabled={active === 0}
          className={clsx(chip, "ml-auto inline-flex items-center gap-1 border-border text-text-secondary")}
        >
          <FilterX size={14} aria-hidden="true" /> Limpiar filtros{active ? ` (${active})` : ""}
        </button>
      </div>
      <Group title="Nido / cavidad" enabled={available.cavity}>
        {dataset.cavities.map((c) => (
          <Chip key={c} active={f.cavities.includes(c)} onClick={() => set({ cavities: toggle(f.cavities, c) })} label={`Nido ${c}`}>
            {c}
          </Chip>
        ))}
      </Group>
      {showVariables && (
        <Group title="Cotas que cuentan para NOK (vacío = todas)" enabled>
          {dataset.variables.map((v) => (
            <Chip key={v.key} active={f.variables.includes(v.key)} onClick={() => set({ variables: toggle(f.variables, v.key) })}>
              {v.name}
            </Chip>
          ))}
        </Group>
      )}
    </Card>
  );
}
