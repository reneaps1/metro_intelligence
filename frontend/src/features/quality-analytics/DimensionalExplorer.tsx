import { Card, CardHeader } from "../../components/ui/Card";
import { Kpi } from "../../components/workbench/Kpi";
import { useAsync } from "../../lib/catalog/hooks";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { fetchVariableDetail } from "../../lib/quality-analytics/api";
import { formatPct } from "../../lib/quality-analytics/filters";
import type { GroupBy, QualityDataset } from "../../lib/quality-analytics/types";
import { BoxplotChart, DailyCpkChart, HistogramChart, IndividualsChart } from "./DimensionalCharts";
import { PinPositionPanel } from "./PinPositionPanel";
import { QualityFilterBar } from "./QualityFilterBar";

// IQ-F5: demo step 3 -- one dimensional variable in depth. IQ-F16: workbench
// look -- uppercase labels, KPI tiles, neutral charts with the NOK accent.

const GROUP_LABEL: Record<GroupBy, string> = {
  cavity: "Nido",
  machine: "Máquina",
  shift: "Turno",
  batch: "Lote",
  mold_cavity: "Cavidad de molde",
};
const fmt = (v: number | null | undefined, digits = 4) =>
  v === null || v === undefined ? "—" : v.toLocaleString("es-MX", { maximumFractionDigits: digits });
const index = (v: number | null | undefined) => (v === null || v === undefined ? "—" : v.toFixed(2));

const select = "ml-2 rounded-md border border-border bg-surface px-2 py-1.5 text-sm font-semibold normal-case tracking-normal text-text-primary";

export function DimensionalExplorer({ dataset }: { dataset: QualityDataset }) {
  const { qualityFilters: f, setQualityFilters } = useDemoSession();
  const offset = dataset.utc_offset_minutes ?? 0;
  const detail = useAsync(
    () => fetchVariableDetail(f, offset),
    [JSON.stringify({ ...f, variables: [], stations: [], granularity: "" })],
  );
  const d = detail.data;
  const available = dataset.available_filters;
  const groupOptions = (Object.keys(GROUP_LABEL) as GroupBy[]).filter((g) => Boolean(available[g]));
  const groupLabel = (g: string) =>
    f.groupBy === "cavity" ? `N${g}` : f.groupBy === "mold_cavity" ? `C${g}` : f.groupBy === "shift" ? `T. ${g}` : g;
  const reported = (d?.nok_basis ?? dataset.nok_basis) === "reported";
  const noSpec = d ? d.spec.lsl === null && d.spec.usl === null : false;

  return (
    <div className="space-y-4">
      <QualityFilterBar dataset={dataset} showVariables={false} />
      <Card className="flex flex-wrap items-end gap-4">
        <label className="wb-label">
          Cota
          <select
            className={select}
            value={f.detailVariable}
            onChange={(e) => setQualityFilters((prev) => ({ ...prev, detailVariable: e.target.value }))}
            aria-label="Cota a explorar"
          >
            {dataset.variables.map((v) => (
              <option key={v.key} value={v.key}>
                {v.name} ({v.key})
              </option>
            ))}
          </select>
        </label>
        <label className="wb-label">
          Comparar por
          <select
            className={select}
            value={f.groupBy}
            onChange={(e) => setQualityFilters((prev) => ({ ...prev, groupBy: e.target.value as GroupBy }))}
            aria-label="Comparar por"
          >
            {groupOptions.map((g) => (
              <option key={g} value={g}>
                {GROUP_LABEL[g]}
              </option>
            ))}
          </select>
        </label>
        {d && (
          <p className="text-sm text-text-secondary">
            {reported && noSpec
              ? "Sin tolerancias en la fuente: los NOK marcados son piezas rechazadas por la estación que mide esta cota."
              : `Especificación: nominal ${fmt(d.spec.nominal)} ${d.spec.unit} · LSL ${fmt(d.spec.lsl)} · USL ${fmt(d.spec.usl)}`}
          </p>
        )}
      </Card>

      {detail.error && (
        <p role="alert" className="text-sm text-status-nok">
          {detail.error}
        </p>
      )}
      {detail.loading && !d && <p className="text-sm text-text-secondary">Calculando…</p>}

      {d && d.n > 0 && (
        <>
          <div className="wb-kpis" aria-label="Estadística de la cota">
            <Kpi size="sm" label="Mediciones" value={d.n.toLocaleString("es-MX")} />
            <Kpi size="sm" label="Media" value={fmt(d.mean)} hint={`desv. est. ${fmt(d.std)}`} />
            <Kpi size="sm" label="Rango" value={`${fmt(d.min)} – ${fmt(d.max)}`} />
            <Kpi
              size="sm"
              label="NOK"
              value={formatPct(d.nok_rate)}
              hint={`${d.nok.toLocaleString("es-MX")} ${d.nok_label ?? "fuera de tolerancia"}`}
              tone="nok"
            />
            <Kpi size="sm" label="Cp" value={index(d.capability?.cp)} hint={d.capability?.cp === null ? d.capability?.reason ?? undefined : "global (desv. total)"} />
            <Kpi size="sm" label="Cpk" value={index(d.capability?.cpk)} hint={d.capability?.cpk === null ? d.capability?.reason ?? undefined : "global (desv. total)"} />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader title="Distribución y tolerancias" />
              <HistogramChart detail={d} />
            </Card>
            <Card>
              <CardHeader title={`Comparativo por ${GROUP_LABEL[f.groupBy].toLowerCase()}`} />
              <BoxplotChart groups={d.groups} spec={d.spec} label={groupLabel} />
              <p className="text-xs text-text-secondary">
                Caja = Q1–Q3, línea = mediana, bigotes = 1.5 × IQR; puntos = extremos atípicos. Resaltado, el grupo con la
                mayor tasa NOK.
              </p>
            </Card>
            <Card>
              <CardHeader title="Carta de individuales (I-MR)" />
              <IndividualsChart detail={d} offsetMinutes={offset} />
              <p className="text-xs text-text-secondary">
                {noSpec ? "Sin límites de especificación en la fuente." : "Discontinuo = límites de especificación (cliente)."}{" "}
                Punteado = límites de control calculados del proceso ({d.control_limits?.engine ?? "—"}). Triángulos = piezas{" "}
                {reported ? "rechazadas por su estación" : "fuera de tolerancia"}; círculos huecos = fuera de control.
                {offset ? " Horas en hora local de planta." : ""}
                {d.series_thinned ? " Se muestra una muestra uniforme de la serie; los límites usan todos los datos." : ""}
              </p>
            </Card>
            <Card>
              <CardHeader title="Evolución diaria de Cpk" />
              <DailyCpkChart detail={d} />
            </Card>
          </div>
        </>
      )}
      {d && d.n === 0 && <p className="text-sm text-text-secondary">No hay mediciones para la selección actual.</p>}
      {(dataset.pin_pairs?.length ?? 0) > 0 && <PinPositionPanel dataset={dataset} />}
    </div>
  );
}
