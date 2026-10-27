import { useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { Database, Trash2, Upload, X } from "lucide-react";
import { Card } from "../../../components/ui/Card";
import { useAsync } from "../../../lib/catalog/hooks";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { fetchDatasets } from "../../../lib/quality-analytics/api";
import { DEFAULT_QUALITY_FILTERS, DEMO_DATASET_ID } from "../../../lib/quality-analytics/filters";
import { deleteImportedDataset } from "../../../lib/quality-analytics/imports";
import type { QualityDataset } from "../../../lib/quality-analytics/types";
import { DimensionalExplorer } from "../../quality-analytics/DimensionalExplorer";
import { DimensionalImport } from "../../quality-analytics/DimensionalImport";
import { QualityOverview } from "../../quality-analytics/QualityOverview";

// IQ-F5/F6: demo steps 2 and 3 share the dataset lookup, the dataset picker
// (demo dataset or a CSV imported in this session) and its origin banner.

function DatasetBanner({ dataset }: { dataset: QualityDataset }) {
  const tone =
    dataset.source_type === "SIMULATED"
      ? "bg-status-warning-bg text-status-warning"
      : dataset.source_type === "IMPORTED"
        ? "bg-status-info-bg text-status-info"
        : "bg-status-ok-bg text-status-ok";
  return (
    <p className={`flex items-start gap-2 rounded px-3 py-2 text-sm ${tone}`}>
      <Database size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
      <span>
        <strong>{dataset.name}.</strong> {dataset.description}{" "}
        {dataset.source_type === "SIMULATED"
          ? "Los mecanismos de defecto se inyectaron a propósito; se listan en «Verdad conocida del dataset sintético» (paso 2)."
          : dataset.source_type === "IMPORTED"
            ? "Se analiza tal como viene; las conclusiones dependen de la calidad y representatividad del archivo."
            : "Calculado sobre datos reales."}
      </span>
    </p>
  );
}

function filtersFor(ds: QualityDataset) {
  return {
    ...DEFAULT_QUALITY_FILTERS,
    datasetId: ds.id,
    detailVariable: ds.id === DEMO_DATASET_ID ? DEFAULT_QUALITY_FILTERS.detailVariable : (ds.variables[0]?.key ?? ""),
  };
}

function DatasetPicker({
  items,
  dataset,
  onSelect,
  onImported,
  onDiscarded,
}: {
  items: QualityDataset[];
  dataset: QualityDataset;
  onSelect: (ds: QualityDataset) => void;
  onImported: (ds: QualityDataset) => void;
  onDiscarded: (id: string) => void;
}) {
  const [importing, setImporting] = useState(false);
  const [discardError, setDiscardError] = useState<string | null>(null);

  async function discard() {
    setDiscardError(null);
    try {
      await deleteImportedDataset(dataset.id);
      onDiscarded(dataset.id);
    } catch {
      setDiscardError("No se pudo descartar el archivo.");
    }
  }

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs font-semibold text-text-secondary">
          Dataset
          <select
            className="ml-2 max-w-[22rem] rounded border border-border bg-surface px-2 py-1.5 text-sm text-text-primary"
            value={dataset.id}
            onChange={(e) => {
              const ds = items.find((d) => d.id === e.target.value);
              if (ds) onSelect(ds);
            }}
            aria-label="Dataset analizado"
          >
            {items.map((d) => (
              <option key={d.id} value={d.id}>
                {d.source_type === "IMPORTED" ? "Importado · " : "Demo · "}
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          aria-expanded={importing}
          onClick={() => setImporting((v) => !v)}
          className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-sm text-text-secondary hover:border-brand-primary"
        >
          {importing ? <X size={14} aria-hidden="true" /> : <Upload size={14} aria-hidden="true" />}
          {importing ? "Cerrar importación" : "Importar CSV propio"}
        </button>
        {dataset.source_type === "IMPORTED" && (
          <button
            type="button"
            onClick={() => void discard()}
            className="inline-flex items-center gap-1 rounded border border-border px-3 py-1.5 text-sm text-text-secondary hover:border-status-nok"
          >
            <Trash2 size={14} aria-hidden="true" /> Descartar archivo
          </button>
        )}
      </div>
      {discardError && <p className="text-sm text-status-nok">{discardError}</p>}
      {importing && (
        <DimensionalImport
          onImported={(ds) => {
            setImporting(false);
            onImported(ds);
          }}
        />
      )}
    </Card>
  );
}

function DatasetStep({ children }: { children: (dataset: QualityDataset) => ReactNode }) {
  const { qualityFilters, setQualityFilters } = useDemoSession();
  const datasets = useAsync(fetchDatasets, []);
  // Imported in this view: shown before the list is refetched, so selecting it
  // never looks like a "missing" dataset.
  const [added, setAdded] = useState<QualityDataset[]>([]);
  const [params, setParams] = useSearchParams();
  const requested = params.get("dataset");

  const fetched = datasets.data?.items ?? [];
  const items = [...fetched, ...added.filter((a) => !fetched.some((d) => d.id === a.id))];
  const dataset = items.find((d) => d.id === qualityFilters.datasetId) ?? null;
  const select = (ds: QualityDataset) => setQualityFilters(() => filtersFor(ds));

  // Deep link from the import page: /demo/industrial-quality/quality?dataset=<id>
  useEffect(() => {
    if (!requested || !datasets.data) return;
    const ds = datasets.data.items.find((d) => d.id === requested);
    if (ds) select(ds);
    setParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, when the list arrives
  }, [requested, datasets.data]);

  // An imported dataset expires (in-memory TTL) or was discarded: back to the demo dataset.
  const missing = Boolean(datasets.data) && !datasets.loading && !dataset && !requested;
  useEffect(() => {
    if (missing) setQualityFilters(() => DEFAULT_QUALITY_FILTERS);
  }, [missing, setQualityFilters]);

  if (datasets.error) return <p role="alert" className="text-sm text-status-nok">{datasets.error}</p>;
  if (!dataset) return <p className="text-sm text-text-secondary">Cargando dataset…</p>;
  return (
    <div className="space-y-4">
      <DatasetPicker
        items={items}
        dataset={dataset}
        onSelect={select}
        onImported={(ds) => {
          setAdded((prev) => [...prev, ds]);
          select(ds);
          datasets.refetch();
        }}
        onDiscarded={(id) => {
          setAdded((prev) => prev.filter((d) => d.id !== id));
          setQualityFilters(() => DEFAULT_QUALITY_FILTERS);
          datasets.refetch();
        }}
      />
      <DatasetBanner dataset={dataset} />
      {children(dataset)}
    </div>
  );
}

export function QualityStep() {
  return <DatasetStep>{(dataset) => <QualityOverview key={dataset.id} dataset={dataset} />}</DatasetStep>;
}

export function DimensionalStep() {
  return <DatasetStep>{(dataset) => <DimensionalExplorer key={dataset.id} dataset={dataset} />}</DatasetStep>;
}
