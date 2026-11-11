import { useCallback, useEffect, useState } from "react";
import { Boxes, ChevronDown } from "lucide-react";
import clsx from "clsx";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { groupParts, partFilters, storePartId } from "../../../lib/demo/part";
import { fetchDatasets } from "../../../lib/quality-analytics/api";
import type { QualityDataset } from "../../../lib/quality-analytics/types";
import { useAsync } from "../../../lib/catalog/hooks";
import { usePopover } from "./usePopover";

// IQ-F22: the single "Pieza" control of the workbench. Choosing a part sets the
// dataset every part-aware step uses (Diagnóstico, Exploración, Laboratorio IA
// and the line panel); simulated-process views do not depend on it.

const ORIGIN: Record<QualityDataset["source_type"], string> = {
  REAL: "Real",
  SIMULATED: "Simulado",
  IMPORTED: "Importado",
};

export function PartControl() {
  const { qualityFilters, setQualityFilters } = useDemoSession();
  const datasets = useAsync(fetchDatasets, []);
  const items = datasets.data?.items ?? [];
  const [open, setOpen] = useState(false);
  const close = useCallback(() => setOpen(false), []);
  const ref = usePopover(open, close);
  const [pending, setPending] = useState(qualityFilters.datasetId);
  useEffect(() => {
    if (open) setPending(qualityFilters.datasetId);
  }, [open, qualityFilters.datasetId]);

  const active = items.find((d) => d.id === qualityFilters.datasetId);

  function apply() {
    const ds = items.find((d) => d.id === pending);
    if (ds && ds.id !== qualityFilters.datasetId) {
      setQualityFilters(() => partFilters(ds));
      storePartId(ds.id);
    }
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        title="Pieza analizada: cambiar"
        className="flex min-h-[36px] max-w-[320px] items-center gap-2 rounded-md border border-border pl-2.5 pr-3 hover:bg-wb-pane-header"
      >
        <Boxes
          size={16}
          className="flex-none text-text-secondary"
          aria-hidden="true"
        />
        <span className="text-xs text-text-secondary">Pieza</span>
        <span className="truncate text-sm font-semibold text-text-primary">
          {active?.name ?? (datasets.loading ? "Cargando…" : "—")}
        </span>
        <ChevronDown
          size={14}
          strokeWidth={2.5}
          className="flex-none text-text-secondary"
          aria-hidden="true"
        />
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Pieza analizada"
          className="absolute right-0 top-full z-dropdown mt-1 max-h-[70vh] w-[420px] max-w-[92vw] overflow-y-auto rounded-md border border-border bg-surface-raised p-3 shadow-md"
        >
          <p className="mb-2 text-[13px] text-text-secondary">
            Cambia la pieza en Diagnóstico, Exploración dimensional, Laboratorio
            IA y Panel de línea. Las vistas del proceso simulado no dependen de
            ella.
          </p>
          {datasets.error && (
            <p role="alert" className="text-sm text-status-nok">
              {datasets.error}
            </p>
          )}
          <div
            role="radiogroup"
            aria-label="Pieza analizada"
            className="flex flex-col gap-3"
          >
            {groupParts(items).map((group) => (
              <div key={group.line} className="flex flex-col gap-1">
                <span className="wb-label">{group.line}</span>
                {group.items.map((ds) => {
                  const checked = ds.id === pending;
                  return (
                    <button
                      key={ds.id}
                      type="button"
                      role="radio"
                      aria-checked={checked}
                      onClick={() => setPending(ds.id)}
                      className={clsx(
                        "flex min-h-[44px] items-start gap-2.5 rounded-md border px-2.5 py-1.5 text-left",
                        checked
                          ? "border-brand-primary bg-wb-selected"
                          : "border-border hover:bg-wb-pane-header",
                      )}
                    >
                      <span
                        aria-hidden="true"
                        className={clsx(
                          "mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded-full border-2",
                          checked ? "border-brand-primary" : "border-border",
                        )}
                      >
                        {checked && (
                          <span className="h-1.5 w-1.5 rounded-full bg-brand-primary" />
                        )}
                      </span>
                      <span className="flex-1">
                        <span className="block text-sm font-medium text-text-primary">
                          {ds.name}
                        </span>
                        <span className="block text-xs text-text-secondary">
                          {ORIGIN[ds.source_type]} ·{" "}
                          {ds.pieces.toLocaleString("es-MX")} piezas
                          {ds.stations && ds.stations.length > 0
                            ? ` · ${ds.stations.length} estaciones`
                            : ""}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={close}
              className="min-h-[36px] rounded-md border border-border px-3 text-sm hover:bg-wb-pane-header"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={apply}
              disabled={!items.some((d) => d.id === pending)}
              className="min-h-[36px] rounded-md bg-brand-primary px-3 text-sm font-semibold text-text-on-brand disabled:opacity-40"
            >
              Aplicar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
