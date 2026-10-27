import { Database } from "lucide-react";
import { useAsync } from "../../../lib/catalog/hooks";
import { useDemoSession } from "../../../lib/demo/DemoSessionProvider";
import { fetchDatasets } from "../../../lib/quality-analytics/api";
import type { QualityDataset } from "../../../lib/quality-analytics/types";
import { DimensionalExplorer } from "../../quality-analytics/DimensionalExplorer";
import { QualityOverview } from "../../quality-analytics/QualityOverview";

// IQ-F5: demo steps 2 and 3 share the dataset lookup and its origin banner.

function DatasetBanner({ dataset }: { dataset: QualityDataset }) {
  const simulated = dataset.source_type === "SIMULATED";
  return (
    <p
      className={
        simulated
          ? "flex items-start gap-2 rounded bg-status-warning-bg px-3 py-2 text-sm text-status-warning"
          : "flex items-start gap-2 rounded bg-status-ok-bg px-3 py-2 text-sm text-status-ok"
      }
    >
      <Database size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
      <span>
        <strong>{dataset.name}.</strong> {dataset.description}{" "}
        {simulated
          ? "Los mecanismos de defecto se inyectaron a propósito; se listan en «Verdad conocida del dataset sintético» (paso 2)."
          : "Calculado sobre un archivo importado."}
      </span>
    </p>
  );
}

function useDataset() {
  const { qualityFilters } = useDemoSession();
  const datasets = useAsync(fetchDatasets, []);
  const dataset = datasets.data?.items.find((d) => d.id === qualityFilters.datasetId) ?? null;
  return { datasets, dataset };
}

export function QualityStep() {
  const { datasets, dataset } = useDataset();
  if (datasets.error) return <p role="alert" className="text-sm text-status-nok">{datasets.error}</p>;
  if (!dataset) return <p className="text-sm text-text-secondary">Cargando dataset…</p>;
  return (
    <div className="space-y-4">
      <DatasetBanner dataset={dataset} />
      <QualityOverview dataset={dataset} />
    </div>
  );
}

export function DimensionalStep() {
  const { datasets, dataset } = useDataset();
  if (datasets.error) return <p role="alert" className="text-sm text-status-nok">{datasets.error}</p>;
  if (!dataset) return <p className="text-sm text-text-secondary">Cargando dataset…</p>;
  return (
    <div className="space-y-4">
      <DatasetBanner dataset={dataset} />
      <DimensionalExplorer dataset={dataset} />
    </div>
  );
}
