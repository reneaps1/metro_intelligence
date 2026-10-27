import { useState } from "react";
import { ChevronDown, ChevronRight, Download, FlaskConical } from "lucide-react";
import clsx from "clsx";
import { Card, CardHeader } from "../../components/ui/Card";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { useAsync } from "../../lib/catalog/hooks";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import { fetchOverview, fetchReportSummary } from "../../lib/quality-analytics/api";
import { cavityCsv, downloadText } from "../../lib/quality-analytics/export";
import { formatPct } from "../../lib/quality-analytics/filters";
import type { Granularity, QualityDataset, ReportSummary, SourceReported } from "../../lib/quality-analytics/types";
import { CavityHeatmap, CavityRateChart, NokTrendChart, ParetoChart } from "./QualityCharts";
import { QualityFilterBar } from "./QualityFilterBar";

// IQ-F5: demo step 2 -- quality diagnosis over the selected dimensional dataset.

const GRANULARITIES: { id: Granularity; label: string }[] = [
  { id: "day", label: "Día" },
  { id: "hour", label: "Hora" },
  { id: "shift", label: "Turno" },
];

const n = (v: number) => v.toLocaleString("es-MX");

function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: "nok" }) {
  return (
    <div className="rounded border border-border bg-surface p-3">
      <p className="text-xs text-text-secondary">{label}</p>
      <p className={clsx("font-mono text-xl font-semibold", tone === "nok" ? "text-status-nok" : "text-text-primary")}>{value}</p>
      {hint && <p className="text-xs text-text-secondary">{hint}</p>}
    </div>
  );
}

export function QualityOverview({ dataset }: { dataset: QualityDataset }) {
  const { qualityFilters: f, setQualityFilters } = useDemoSession();
  const overview = useAsync(() => fetchOverview(f), [JSON.stringify({ ...f, detailVariable: "", groupBy: "" })]);
  const report = useAsync(fetchReportSummary, []);
  // The private historical report describes the customer's plant, not an uploaded file.
  const showReport = dataset.source_type !== "IMPORTED";
  const data = overview.data;
  const s = data?.summary;
  const varName = (key: string) => dataset.variables.find((v) => v.key === key)?.name ?? key;

  return (
    <div className="space-y-4">
      <QualityFilterBar dataset={dataset} />
      {overview.error && (
        <p role="alert" className="text-sm text-status-nok">
          {overview.error}
        </p>
      )}
      {overview.loading && !data && <p className="text-sm text-text-secondary">Calculando indicadores…</p>}

      {data && s && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6" aria-label="Indicadores de calidad">
            <Kpi label="Grupos inspeccionados" value={n(s.groups)} hint="disparos / grupos de pieza" />
            <Kpi label="Piezas" value={n(s.pieces)} hint={`${n(s.measurements)} mediciones`} />
            <Kpi label="Piezas OK" value={n(s.ok_pieces)} />
            <Kpi
              label="Piezas NOK"
              value={n(s.nok_pieces)}
              hint={`${n(s.measurement_nok)} mediciones NOK`}
              tone="nok"
            />
            <Kpi
              label="Tasa NOK"
              value={formatPct(s.nok_rate)}
              hint={s.nok_rate_ci ? `IC 95 %: ${formatPct(s.nok_rate_ci[0])} – ${formatPct(s.nok_rate_ci[1])}` : undefined}
              tone="nok"
            />
            <Kpi
              label="Nido de mayor riesgo"
              value={s.worst_cavity ? `Nido ${s.worst_cavity.cavity}` : "—"}
              hint={
                s.worst_cavity
                  ? `${formatPct(s.worst_cavity.rate)} · RR ${s.worst_cavity.relative_risk?.toFixed(1) ?? "—"}× vs. resto`
                  : undefined
              }
              tone="nok"
            />
          </div>
          {s.variables_with_tolerance === 0 && (
            <p role="status" className="rounded bg-status-warning-bg px-3 py-2 text-sm text-status-warning">
              Ninguna cota seleccionada tiene tolerancias: la tasa NOK por especificación no es calculable (se muestra 0) y
              no hay nido de mayor riesgo. Usa el OK/NOK de la fuente o define LIE/LSE al importar.
            </p>
          )}
          {s.source_reported && <SourceReportedCard data={s.source_reported} />}
          <p className="text-xs text-text-secondary">
            {s.nok_definition} Cotas con más NOK: {s.top_variables.map(varName).join(", ") || "ninguna"}. Riesgo relativo =
            tasa del nido / tasa conjunta del resto: indica asociación, no causa.
          </p>

          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            <Card>
              <CardHeader
                title="Tendencia NOK"
                action={
                  <div className="flex rounded border border-border" role="group" aria-label="Agrupar tendencia por">
                    {GRANULARITIES.map((g) => (
                      <button
                        key={g.id}
                        type="button"
                        aria-pressed={f.granularity === g.id}
                        onClick={() => setQualityFilters((prev) => ({ ...prev, granularity: g.id }))}
                        className={clsx(
                          "px-2 py-1 text-xs font-medium",
                          f.granularity === g.id ? "bg-brand-primary text-text-on-brand" : "bg-surface text-text-secondary",
                        )}
                      >
                        {g.label}
                      </button>
                    ))}
                  </div>
                }
              />
              <NokTrendChart trend={data.trend} />
            </Card>
            <Card>
              <CardHeader title="Pareto NOK por cota" />
              <ParetoChart pareto={data.pareto} />
            </Card>
            <Card>
              <CardHeader
                title="NOK por nido · IC 95 %"
                action={
                  <button
                    type="button"
                    onClick={() => downloadText("tasa_nok_por_nido.csv", cavityCsv(data.by_cavity))}
                    title="Descargar la tabla agregada por nido (CSV)"
                    className="inline-flex items-center gap-1 whitespace-nowrap rounded border border-border px-2 py-1 text-xs text-text-secondary hover:border-brand-primary"
                  >
                    <Download size={14} aria-hidden="true" /> CSV
                  </button>
                }
              />
              {data.by_cavity.length ? (
                <CavityRateChart rows={data.by_cavity} worst={s.worst_cavity?.cavity ?? null} />
              ) : (
                <p className="text-sm text-text-secondary">El dataset no identifica nido/cavidad.</p>
              )}
            </Card>
            <Card className="lg:col-span-2 xl:col-span-3">
              <CardHeader title="Mapa de calor nido × cota" />
              <CavityHeatmap cells={data.heatmap} variables={dataset.variables} />
            </Card>
          </div>
        </>
      )}

      {showReport && report.data && <ReportCard report={report.data} />}
      {dataset.mechanisms.length > 0 && <Mechanisms items={dataset.mechanisms} />}
    </div>
  );
}

// IQ-F6: the verdict the file brings vs. the one recalculated from the
// specification. They can legitimately differ (in-house limits, other
// characteristics, manual decisions), so they are never merged.
function SourceReportedCard({ data }: { data: SourceReported }) {
  const cells: [string, number, string][] = [
    ["NOK en ambos", data.both_nok, "text-status-nok"],
    ["Solo NOK según la fuente", data.source_only_nok, "text-status-warning"],
    ["Solo NOK recalculado", data.spec_only_nok, "text-status-warning"],
    ["OK en ambos", data.both_ok, "text-status-ok"],
  ];
  return (
    <Card className="space-y-2">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-text-primary">OK/NOK reportado por la fuente vs. recalculado por especificación</p>
        <p className="text-sm text-text-secondary">
          Fuente: <span className="font-mono font-semibold text-status-nok">{formatPct(data.nok_rate)}</span> NOK (
          {n(data.nok_pieces)} de {n(data.pieces_with_verdict)} piezas con veredicto)
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-4">
        {cells.map(([label, value, tone]) => (
          <div key={label} className="rounded border border-border p-2">
            <p className="text-xs text-text-secondary">{label}</p>
            <p className={clsx("font-mono text-lg font-semibold", tone)}>{n(value)}</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-text-secondary">
        {data.definition} Los KPIs de arriba usan el veredicto recalculado con las tolerancias de cada cota.
      </p>
    </Card>
  );
}

function ReportCard({ report }: { report: ReportSummary }) {
  return (
    <Card className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-semibold text-text-primary">{report.title}</p>
        <OriginBadge origin="PRECOMPUTED" />
        {report.illustrative ? (
          <span className="rounded bg-status-warning-bg px-2 py-0.5 text-xs font-semibold text-status-warning">
            Ejemplo ilustrativo (cifras ficticias)
          </span>
        ) : (
          <OriginBadge origin="HISTORICAL" />
        )}
      </div>
      <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2 xl:grid-cols-4">
        <div>
          <dt className="text-xs text-text-secondary">Período</dt>
          <dd className="text-text-primary">{report.period}</dd>
        </div>
        {report.records !== null && (
          <div>
            <dt className="text-xs text-text-secondary">Registros válidos</dt>
            <dd className="font-mono text-text-primary">{n(report.records)}</dd>
          </div>
        )}
        {report.piece_ids !== null && (
          <div>
            <dt className="text-xs text-text-secondary">Identificadores de pieza</dt>
            <dd className="font-mono text-text-primary">{n(report.piece_ids)}</dd>
          </div>
        )}
        {report.critical_nest !== null && (
          <div>
            <dt className="text-xs text-text-secondary">Nido crítico (riesgo relativo)</dt>
            <dd className="font-mono text-text-primary">
              Nido {report.critical_nest}
              {report.critical_nest_relative_risk !== null ? ` · ${report.critical_nest_relative_risk.toFixed(1)}×` : ""}
            </dd>
          </div>
        )}
      </dl>
      <p className="text-xs text-text-secondary">
        Definición de NOK: {report.nok_definition}
        {report.relative_risk_basis ? ` Riesgo relativo: ${report.relative_risk_basis}` : ""}
      </p>
      {report.notes.length > 0 && (
        <ul className="list-disc pl-5 text-xs text-text-secondary">
          {report.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Mechanisms({ items }: { items: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <Card>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 text-left text-sm font-semibold text-text-primary"
      >
        {open ? <ChevronDown size={16} aria-hidden="true" /> : <ChevronRight size={16} aria-hidden="true" />}
        <FlaskConical size={16} className="text-status-warning" aria-hidden="true" />
        Verdad conocida del dataset sintético
      </button>
      {open && (
        <ul className="mt-2 list-disc space-y-1 pl-6 text-sm text-text-secondary">
          {items.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}
