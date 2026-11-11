import { useState } from "react";
import { groupPrefix, groupWords, sideOrCavity } from "../../lib/demo/part";
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Download,
  FlaskConical,
} from "lucide-react";
import { Card, CardHeader } from "../../components/ui/Card";
import { OriginBadge } from "../../components/ui/OriginBadge";
import { Kpi } from "../../components/workbench/Kpi";
import { Notice } from "../../components/workbench/Notice";
import { useAsync } from "../../lib/catalog/hooks";
import { useDemoSession } from "../../lib/demo/DemoSessionProvider";
import {
  fetchOverview,
  fetchReportSummary,
} from "../../lib/quality-analytics/api";
import {
  cavityCsv,
  downloadText,
  nestMoldCsv,
} from "../../lib/quality-analytics/export";
import { formatPct } from "../../lib/quality-analytics/filters";
import type {
  DrawingConcordance,
  Granularity,
  QualityDataset,
  ReportSummary,
  SourceReported,
} from "../../lib/quality-analytics/types";
import {
  CavityHeatmap,
  CavityRateChart,
  NestMoldMatrix,
  NokTrendChart,
  ParetoChart,
  StationParetoChart,
} from "./QualityCharts";
import { QualityFilterBar } from "./QualityFilterBar";

// IQ-F5: demo step 2 -- quality diagnosis over the selected dimensional dataset.

const GRANULARITIES: { id: Granularity; label: string }[] = [
  { id: "day", label: "Día" },
  { id: "hour", label: "Hora" },
  { id: "shift", label: "Turno" },
];

const n = (v: number) => v.toLocaleString("es-MX");

const csvButton = "wb-chip !min-h-[26px] !px-2 !text-xs";

export function QualityOverview({ dataset }: { dataset: QualityDataset }) {
  const { qualityFilters: f, setQualityFilters } = useDemoSession();
  const offset = dataset.utc_offset_minutes ?? 0;
  const overview = useAsync(
    () => fetchOverview(f, offset),
    [JSON.stringify({ ...f, detailVariable: "", groupBy: "" })],
  );
  const report = useAsync(fetchReportSummary, []);
  // The private historical report describes the customer's plant, not an uploaded file.
  const showReport = dataset.source_type !== "IMPORTED";
  const data = overview.data;
  const s = data?.summary;
  const words = groupWords(dataset);
  const varName = (key: string) =>
    dataset.variables.find((v) => v.key === key)?.name ?? key;
  const stationName = (key: string) =>
    dataset.stations?.find((st) => st.key === key)?.name ?? key;
  const reported = (s?.nok_basis ?? dataset.nok_basis) === "reported";
  const moldRows = data?.by_mold_cavity ?? [];
  const nestMold = data?.nest_mold ?? [];

  return (
    <div className="space-y-4">
      <QualityFilterBar dataset={dataset} />
      {overview.error && (
        <p role="alert" className="text-sm text-status-nok">
          {overview.error}
        </p>
      )}
      {overview.loading && !data && (
        <p className="text-sm text-text-secondary">Calculando indicadores…</p>
      )}

      {data && s && (
        <>
          <div className="wb-kpis" aria-label="Indicadores de calidad">
            {dataset.has_groups !== false && (
              <Kpi
                label="Grupos inspeccionados"
                value={n(s.groups)}
                hint="disparos / grupos de pieza"
              />
            )}
            <Kpi
              label="Piezas"
              value={n(s.pieces)}
              hint={`${n(s.measurements)} mediciones`}
            />
            <Kpi label="Piezas OK" value={n(s.ok_pieces)} />
            <Kpi
              label="Piezas NOK"
              value={n(s.nok_pieces)}
              hint={
                reported
                  ? "veredicto de la máquina"
                  : `${n(s.measurement_nok)} mediciones NOK`
              }
              tone="nok"
            />
            <Kpi
              label="Tasa NOK"
              value={formatPct(s.nok_rate)}
              hint={
                s.nok_rate_ci
                  ? `IC 95 %: ${formatPct(s.nok_rate_ci[0])} – ${formatPct(s.nok_rate_ci[1])}`
                  : undefined
              }
              tone="nok"
            />
            <Kpi
              label={`${words.primary} de mayor riesgo`}
              value={
                s.worst_cavity
                  ? `${words.primary} ${s.worst_cavity.cavity}`
                  : "—"
              }
              hint={
                s.worst_cavity
                  ? `${formatPct(s.worst_cavity.rate)} · RR ${s.worst_cavity.relative_risk?.toFixed(1) ?? "—"}× vs. resto`
                  : undefined
              }
            />
            {s.worst_mold_cavity !== undefined &&
              (dataset.mold_cavities?.length ?? 0) > 0 && (
                <Kpi
                  label={`${words.secondary} de mayor riesgo`}
                  value={
                    s.worst_mold_cavity
                      ? `${words.secondary === "Cavidad de molde" ? "Cav." : words.secondary} ${s.worst_mold_cavity.cavity}`
                      : "—"
                  }
                  hint={
                    s.worst_mold_cavity
                      ? `${formatPct(s.worst_mold_cavity.rate)} · RR ${s.worst_mold_cavity.relative_risk?.toFixed(1) ?? "—"}× vs. resto`
                      : undefined
                  }
                />
              )}
          </div>
          {!reported && s.variables_with_tolerance === 0 && (
            <Notice
              role="status"
              attention
              icon={<AlertTriangle size={16} aria-hidden="true" />}
            >
              Ninguna cota seleccionada tiene tolerancias: la tasa NOK por
              especificación no es calculable (se muestra 0) y no hay nido de
              mayor riesgo. Usa el OK/NOK de la fuente o define LIE/LSE al
              importar.
            </Notice>
          )}
          {s.source_reported && <SourceReportedCard data={s.source_reported} />}
          <p className="text-xs text-text-secondary">
            {s.nok_definition}{" "}
            {reported
              ? "Riesgo relativo = tasa del grupo / tasa conjunta del resto: indica asociación, no causa."
              : `Cotas con más NOK: ${s.top_variables.map(varName).join(", ") || "ninguna"}. Riesgo relativo = tasa del nido / tasa conjunta del resto: indica asociación, no causa.`}
            {s.pieces_without_verdict
              ? ` ${n(s.pieces_without_verdict)} piezas sin veredicto quedan fuera del denominador.`
              : ""}
          </p>

          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            <Card>
              <CardHeader
                title="Tendencia NOK"
                action={
                  <div
                    className="wb-seg"
                    role="group"
                    aria-label="Agrupar tendencia por"
                  >
                    {GRANULARITIES.map((g) => (
                      <button
                        key={g.id}
                        type="button"
                        aria-pressed={f.granularity === g.id}
                        onClick={() =>
                          setQualityFilters((prev) => ({
                            ...prev,
                            granularity: g.id,
                          }))
                        }
                        className="!min-h-[26px] !px-2.5 !text-xs"
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
              <CardHeader
                title={
                  reported ? "Dónde falla · 1ª estación" : "Pareto NOK por cota"
                }
              />
              {reported ? (
                <StationParetoChart rows={data.station_pareto ?? []} />
              ) : (
                <ParetoChart pareto={data.pareto} />
              )}
            </Card>
            <Card>
              <CardHeader
                title={`NOK por ${words.primary.toLowerCase()} · IC 95 %`}
                action={
                  <button
                    type="button"
                    onClick={() =>
                      downloadText(
                        "tasa_nok_por_nido.csv",
                        cavityCsv(data.by_cavity),
                      )
                    }
                    title="Descargar la tabla agregada por nido (CSV)"
                    className={csvButton}
                  >
                    <Download size={14} aria-hidden="true" /> CSV
                  </button>
                }
              />
              {data.by_cavity.length ? (
                <CavityRateChart
                  rows={data.by_cavity}
                  worst={s.worst_cavity?.cavity ?? null}
                  prefix={groupPrefix(dataset, "primary") ?? "N"}
                />
              ) : (
                <p className="text-sm text-text-secondary">
                  El dataset no identifica nido/cavidad.
                </p>
              )}
            </Card>
            {reported && data.drawing_concordance && (
              <Card className="lg:col-span-2">
                <CardHeader title="Máquina vs plano · piezas" />
                <DrawingConcordanceTable c={data.drawing_concordance} />
              </Card>
            )}
            {reported && (data.drawing_pareto?.length ?? 0) > 0 && (
              <Card>
                <CardHeader title="Fuera de plano por característica" />
                <ParetoChart pareto={data.drawing_pareto ?? []} />
                <p className="text-xs text-text-secondary">
                  Mediciones fuera de los límites del plano. Descriptivo: el
                  veredicto oficial sigue siendo el de la máquina.
                </p>
              </Card>
            )}
            {moldRows.length > 0 && (
              <Card className="lg:col-span-2">
                <CardHeader
                  title={`NOK por ${words.secondary.toLowerCase()} · IC 95 %`}
                  action={
                    <button
                      type="button"
                      onClick={() =>
                        downloadText(
                          "tasa_nok_por_cavidad_molde.csv",
                          cavityCsv(moldRows, "cavidad_molde"),
                        )
                      }
                      title="Descargar la tabla agregada por cavidad de molde (CSV)"
                      className={csvButton}
                    >
                      <Download size={14} aria-hidden="true" /> CSV
                    </button>
                  }
                />
                <CavityRateChart
                  rows={moldRows}
                  worst={s.worst_mold_cavity?.cavity ?? null}
                  prefix={groupPrefix(dataset, "secondary") ?? "C"}
                  height={260}
                />
              </Card>
            )}
            {dataset.data_quality &&
              Object.keys(dataset.data_quality).length > 0 && (
                <DataQualityCard counts={dataset.data_quality} />
              )}
            <Card className="lg:col-span-2 xl:col-span-3">
              <CardHeader
                title={
                  data.heatmap_axis === "station"
                    ? "Mapa de calor nido × estación (primera que falla)"
                    : "Mapa de calor nido × cota"
                }
              />
              {data.heatmap_axis === "station" ? (
                <CavityHeatmap
                  cells={data.heatmap}
                  rowName={stationName}
                  rowHeader="Estación"
                  groupLabel={words.primary}
                  countLabel={`piezas NOK atribuidas a esa estación en ese ${words.primary.toLowerCase()}`}
                />
              ) : (
                <CavityHeatmap
                  cells={data.heatmap}
                  rowName={varName}
                  groupLabel={words.primary}
                />
              )}
            </Card>
            {nestMold.length > 0 && (
              <Card className="lg:col-span-2 xl:col-span-3">
                <CardHeader
                  title={`NOK por ${words.primary.toLowerCase()} × ${words.secondary.toLowerCase()}`}
                  action={
                    <button
                      type="button"
                      onClick={() =>
                        downloadText(
                          "tasa_nok_nido_x_cavidad.csv",
                          nestMoldCsv(nestMold),
                        )
                      }
                      title="Descargar la matriz agregada nido × cavidad de molde (CSV)"
                      className={csvButton}
                    >
                      <Download size={14} aria-hidden="true" /> CSV
                    </button>
                  }
                />
                <NestMoldMatrix
                  cells={nestMold}
                  primary={words.primary}
                  secondary={words.secondary}
                  secondaryName={(v) => sideOrCavity(dataset, v)}
                />
              </Card>
            )}
          </div>
        </>
      )}

      {showReport && report.data && <ReportCard report={report.data} />}
      {dataset.mechanisms.length > 0 && (
        <Mechanisms items={dataset.mechanisms} />
      )}
    </div>
  );
}

// IQ-F10: what the offline conversion of the REAL export found -- counts only.
const DATA_QUALITY_ROWS: [string, string, string][] = [
  [
    "ids_total",
    "Identificadores en el export",
    "piezas distintas antes de excluir",
  ],
  [
    "empty_cycles_excluded",
    "Ciclos vacíos excluidos",
    "estación fallida y todas las cotas en 0",
  ],
  [
    "repeated_signature_pieces",
    "Piezas con valores repetidos",
    "misma combinación exacta de cotas repetida muchas veces: sospecha de dato congelado",
  ],
  [
    "sentinel_values",
    "Valores centinela descartados",
    "lecturas fuera de rango físico, tratadas como faltantes",
  ],
  [
    "grouping_out_of_range",
    "Nido / cavidad fuera de rango",
    "se tratan como sin nido / cavidad",
  ],
  [
    "grouping_remapped",
    "Nido remapeado (crudo → normalizado)",
    "el número reportado traía un desfase conocido (p. ej. 13 → 1); se conserva el valor crudo",
  ],
  [
    "rows_malformed",
    "Filas con formato inconsistente",
    "no se pudieron leer y se contaron, no se ocultaron",
  ],
];

function DataQualityCard({ counts }: { counts: Record<string, number> }) {
  const rows = DATA_QUALITY_ROWS.filter(([key]) => counts[key] !== undefined);
  return (
    <Card>
      <section aria-label="Calidad del dato" className="space-y-2">
        <CardHeader title="Calidad del dato" />
        <dl className="space-y-1.5 text-sm">
          {rows.map(([key, label, hint]) => (
            <div
              key={key}
              className="flex items-baseline justify-between gap-3"
              title={hint}
            >
              <dt className="text-text-secondary">{label}</dt>
              <dd
                className={
                  key === "repeated_signature_pieces" && counts[key] > 0
                    ? "wb-nok font-mono font-semibold"
                    : "font-mono font-semibold text-text-primary"
                }
              >
                {n(counts[key])}
              </dd>
            </div>
          ))}
        </dl>
        <p className="text-xs text-text-secondary">
          Conteos de la conversión fuera de línea, no piezas rechazadas.
          «Excluir piezas con valores repetidos» en los filtros muestra su
          efecto en los indicadores.
        </p>
      </section>
    </Card>
  );
}

// IQ-F6: the verdict the file brings vs. the one recalculated from the
// specification. They can legitimately differ (in-house limits, other
// characteristics, manual decisions), so they are never merged.
function SourceReportedCard({ data }: { data: SourceReported }) {
  const cells: [string, number, "nok" | undefined][] = [
    ["NOK en ambos", data.both_nok, "nok"],
    ["Solo NOK según la fuente", data.source_only_nok, undefined],
    ["Solo NOK recalculado", data.spec_only_nok, undefined],
    ["OK en ambos", data.both_ok, undefined],
  ];
  return (
    <Card className="space-y-2">
      <CardHeader
        title="OK/NOK reportado por la fuente vs. recalculado por especificación"
        action={
          <p className="text-sm text-text-secondary">
            Fuente:{" "}
            <span className="wb-nok font-mono font-semibold">
              {formatPct(data.nok_rate)}
            </span>{" "}
            NOK ({n(data.nok_pieces)} de {n(data.pieces_with_verdict)} piezas
            con veredicto)
          </p>
        }
      />
      <div className="grid gap-2 sm:grid-cols-4">
        {cells.map(([label, value, tone]) => (
          <Kpi
            key={label}
            label={label}
            value={n(value)}
            tone={tone}
            size="sm"
          />
        ))}
      </div>
      <p className="text-xs text-text-secondary">
        {data.definition} Los KPIs de arriba usan el veredicto recalculado con
        las tolerancias de cada cota.
      </p>
    </Card>
  );
}

function ReportCard({ report }: { report: ReportSummary }) {
  return (
    <Card className="space-y-2">
      <CardHeader
        title={report.title}
        action={
          <div className="flex flex-wrap items-center gap-2">
            <OriginBadge origin="PRECOMPUTED" />
            {report.illustrative ? (
              <span className="wb-tag dashed">
                Ejemplo ilustrativo (cifras ficticias)
              </span>
            ) : (
              <OriginBadge origin="HISTORICAL" />
            )}
          </div>
        }
      />
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
            <dt className="text-xs text-text-secondary">
              Identificadores de pieza
            </dt>
            <dd className="font-mono text-text-primary">
              {n(report.piece_ids)}
            </dd>
          </div>
        )}
        {report.critical_nest !== null && (
          <div>
            <dt className="text-xs text-text-secondary">
              Nido crítico (riesgo relativo)
            </dt>
            <dd className="font-mono text-text-primary">
              Nido {report.critical_nest}
              {report.critical_nest_relative_risk !== null
                ? ` · ${report.critical_nest_relative_risk.toFixed(1)}×`
                : ""}
            </dd>
          </div>
        )}
      </dl>
      <p className="text-xs text-text-secondary">
        Definición de NOK: {report.nok_definition}
        {report.relative_risk_basis
          ? ` Riesgo relativo: ${report.relative_risk_basis}`
          : ""}
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
        {open ? (
          <ChevronDown size={16} aria-hidden="true" />
        ) : (
          <ChevronRight size={16} aria-hidden="true" />
        )}
        <FlaskConical
          size={16}
          className="text-text-secondary"
          aria-hidden="true"
        />
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

/** IQ-F28: 2x2 machine verdict vs. drawing limits; highlights pieces the machine passed but the drawing would not. */
export function DrawingConcordanceTable({ c }: { c: DrawingConcordance }) {
  const total =
    c.machine_ok_drawing_ok +
    c.machine_ok_drawing_out +
    c.machine_nok_drawing_ok +
    c.machine_nok_drawing_out;
  const pct = (k: number) => (total ? formatPct(k / total) : "—");
  const cell = (k: number, accent = false) => (
    <td
      className={
        accent
          ? "p-2 text-right font-mono font-semibold text-[var(--wb-nok)]"
          : "p-2 text-right font-mono"
      }
    >
      {k.toLocaleString("es-MX")}{" "}
      <span className="text-xs text-text-secondary">({pct(k)})</span>
    </td>
  );
  return (
    <div className="space-y-2">
      <table className="w-full text-sm" aria-label="Máquina vs plano">
        <thead>
          <tr className="text-left text-xs text-text-secondary">
            <th className="p-2 font-medium">Máquina \ Plano</th>
            <th className="p-2 text-right font-medium">Dentro del plano</th>
            <th className="p-2 text-right font-medium">Fuera del plano</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-border">
            <th className="p-2 text-left font-medium">OK</th>
            {cell(c.machine_ok_drawing_ok)}
            {cell(c.machine_ok_drawing_out, c.machine_ok_drawing_out > 0)}
          </tr>
          <tr className="border-t border-border">
            <th className="p-2 text-left font-medium">NOK</th>
            {cell(c.machine_nok_drawing_ok)}
            {cell(c.machine_nok_drawing_out)}
          </tr>
        </tbody>
      </table>
      <p className="text-xs text-text-secondary">
        Resaltado: piezas que la máquina aprobó con alguna característica fuera
        de los límites del plano — revisar si la máquina usa límites distintos
        al plano.{" "}
        {c.not_measured
          ? `${c.not_measured.toLocaleString("es-MX")} piezas sin esas características medidas.`
          : ""}
      </p>
    </div>
  );
}
