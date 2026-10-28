import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  ErrorBar,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { WB, axisTick, gridProps, lineLabel, rampFill, refLine, secondaryLine, tooltipStyle } from "../../lib/demo/chartTheme";
import { formatPct } from "../../lib/quality-analytics/filters";
import type { CavityRate, HeatmapCell, ParetoRow, StationParetoRow, TrendBucket } from "../../lib/quality-analytics/types";

// IQ-F5: charts for the quality diagnosis step. Rates are shown in %, always
// next to their denominator (pieces) in tooltips. IQ-F16: workbench chart
// theme -- neutral bars, the worst group in the muted NOK accent.

const HOUR_MS = 3_600_000;

export function NokTrendChart({ trend }: { trend: TrendBucket[] }) {
  // Hourly buckets: a stretch without production (e.g. a stop) breaks the line instead of bridging it.
  const data: { label: string; pct: number | null; rate: number | null; nok: number; pieces: number }[] = [];
  trend.forEach((b, i) => {
    const prev = trend[i - 1];
    if (prev?.start && b.start && b.bucket.includes("T") && Date.parse(b.start) - Date.parse(prev.start) > 1.5 * HOUR_MS) {
      data.push({ label: "sin producción", pct: null, rate: null, nok: 0, pieces: 0 });
    }
    data.push({ ...b, pct: b.rate === null ? null : b.rate * 100, label: b.bucket.replace("T", " ") });
  });
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey="label" tick={axisTick} minTickGap={24} />
        <YAxis tick={axisTick} width={48} unit=" %" />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(_v: number, _n: string, item: { payload?: TrendBucket }) => [
            `${formatPct(item.payload?.rate ?? null)} (${item.payload?.nok ?? 0} / ${item.payload?.pieces ?? 0} piezas)`,
            "Tasa NOK",
          ]}
        />
        <Line
          dataKey="pct"
          stroke={WB.nok}
          strokeWidth={2}
          dot={data.length < 40 ? { r: 2.5, fill: WB.nok, strokeWidth: 0 } : false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ParetoChart({ pareto }: { pareto: ParetoRow[] }) {
  const data = pareto
    .filter((r) => r.nok > 0)
    .map((r) => ({ ...r, cumulative: r.cumulative_pct === null ? null : r.cumulative_pct * 100 }));
  if (data.length === 0) return <p className="text-sm text-text-secondary">Sin mediciones NOK en la selección.</p>;
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 56, left: 32 }}>
        <XAxis dataKey="name" tick={{ ...axisTick, fontSize: 10 }} angle={-25} textAnchor="end" interval={0} />
        <YAxis yAxisId="count" tick={axisTick} width={40} allowDecimals={false} />
        <YAxis yAxisId="pct" orientation="right" tick={axisTick} width={40} domain={[0, 100]} unit=" %" />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value: number, name: string, item: { payload?: ParetoRow }) =>
            name === "cumulative"
              ? [`${value.toFixed(1)} %`, "Acumulado"]
              : [`${value} (↑${item.payload?.above ?? 0} / ↓${item.payload?.below ?? 0})`, "Mediciones NOK"]
          }
        />
        <Bar yAxisId="count" dataKey="nok" fill={WB.bar} isAnimationActive={false} />
        <Line yAxisId="pct" dataKey="cumulative" {...secondaryLine} dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

// IQ-F10: NOK pieces by the first station that failed (process order).
export function StationParetoChart({ rows }: { rows: StationParetoRow[] }) {
  const data = rows
    .filter((r) => r.nok > 0)
    .map((r) => ({ ...r, cumulative: r.cumulative_pct === null ? null : r.cumulative_pct * 100 }));
  if (data.length === 0) return <p className="text-sm text-text-secondary">Sin piezas NOK en la selección.</p>;
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 80, left: 24 }}>
        <XAxis dataKey="name" tick={{ ...axisTick, fontSize: 9 }} angle={-40} textAnchor="end" interval={0} />
        <YAxis yAxisId="count" tick={axisTick} width={48} allowDecimals={false} />
        <YAxis yAxisId="pct" orientation="right" tick={axisTick} width={40} domain={[0, 100]} unit=" %" />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(value: number, name: string, item: { payload?: StationParetoRow }) =>
            name === "cumulative"
              ? [`${value.toFixed(1)} %`, "Acumulado"]
              : [
                  `${value.toLocaleString("es-MX")} piezas (${formatPct(item.payload?.share ?? null, 1)}) · falla registrada en ${(item.payload?.fails_any ?? 0).toLocaleString("es-MX")}`,
                  "Primera estación que falla",
                ]
          }
        />
        <Bar yAxisId="count" dataKey="nok" fill={WB.bar} isAnimationActive={false} />
        <Line yAxisId="pct" dataKey="cumulative" {...secondaryLine} dot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function CavityRateChart({
  rows,
  worst,
  prefix = "N",
  height = 240,
}: {
  rows: CavityRate[];
  worst: number | null;
  /** Axis label prefix: "N" for nests, "C" for mold cavities. */
  prefix?: string;
  height?: number;
}) {
  const data = rows.map((r) => ({
    ...r,
    label: `${prefix}${r.cavity}`,
    pct: r.rate === null ? 0 : r.rate * 100,
    ci:
      r.rate === null || r.ci_low === null || r.ci_high === null
        ? [0, 0]
        : [(r.rate - r.ci_low) * 100, (r.ci_high - r.rate) * 100],
  }));
  // Pooled rate of the groups shown: the reference every bar is read against.
  const pieces = rows.reduce((a, r) => a + r.pieces, 0);
  const pooled = pieces ? (rows.reduce((a, r) => a + r.nok, 0) / pieces) * 100 : null;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 14, right: pooled === null ? 8 : 76, bottom: 0, left: 0 }}>
        <XAxis dataKey="label" tick={{ ...axisTick, fontSize: data.length > 16 ? 9 : 11 }} interval={0} />
        <YAxis tick={axisTick} width={48} unit=" %" />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(_v: number, _n: string, item: { payload?: CavityRate }) => {
            const p = item.payload;
            const rr = p?.relative_risk ? ` · RR ${p.relative_risk.toFixed(1)}×` : "";
            return [`${formatPct(p?.rate ?? null)} (${p?.nok ?? 0} / ${p?.pieces ?? 0})${rr}`, "Tasa NOK"];
          }}
        />
        <Bar dataKey="pct" isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.cavity} fill={d.cavity === worst ? WB.nok : WB.bar} />
          ))}
          <ErrorBar dataKey="ci" width={4} stroke="var(--text-secondary)" />
        </Bar>
        {pooled !== null && (
          <ReferenceLine y={pooled} {...refLine} ifOverflow="extendDomain" label={lineLabel(`Media ${pooled.toFixed(1)}%`)} />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CavityHeatmap({
  cells,
  rowName,
  rowHeader = "Cota",
  countLabel = "mediciones NOK de esa cota en ese nido",
}: {
  cells: HeatmapCell[];
  /** Display name of a row key (variable, or station on the reported basis). */
  rowName: (key: string) => string;
  rowHeader?: string;
  countLabel?: string;
}) {
  const cavities = [...new Set(cells.map((c) => c.cavity))].sort((a, b) => a - b);
  const keys = [...new Set(cells.map((c) => c.variable))];
  const max = Math.max(...cells.map((c) => c.rate ?? 0), 0);
  const name = rowName;
  const cell = (cav: number, key: string) => cells.find((c) => c.cavity === cav && c.variable === key);
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-0.5 text-xs" aria-label={`Mapa de calor nido por ${rowHeader.toLowerCase()}`}>
        <thead>
          <tr>
            <th className="sticky left-0 bg-surface px-1 text-left font-medium text-text-secondary">{rowHeader} \ Nido</th>
            {cavities.map((c) => (
              <th key={c} className="px-1 font-mono font-medium text-text-secondary">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {keys.map((key) => (
            <tr key={key}>
              <th scope="row" className="sticky left-0 whitespace-nowrap bg-surface px-1 text-left font-medium text-text-primary">
                {name(key)}
              </th>
              {cavities.map((cav) => {
                const c = cell(cav, key);
                // Neutral single-hue ramp (workbench chart theme); the busiest cell is outlined in the NOK accent.
                const fill = max > 0 && c?.rate ? rampFill(c.rate / max) : null;
                const top = max > 0 && c?.rate === max;
                return (
                  <td
                    key={cav}
                    title={`${name(key)} · nido ${cav}: ${c?.nok ?? 0} NOK / ${c?.pieces ?? 0} piezas (${formatPct(c?.rate ?? null)})`}
                    className="h-7 min-w-[34px] rounded-sm text-center font-mono text-[10px]"
                    style={{
                      background: fill?.background ?? "var(--bg-app)",
                      color: fill?.color ?? "var(--text-primary)",
                      boxShadow: top ? `inset 0 0 0 2px ${WB.nok}` : undefined,
                    }}
                  >
                    {c?.nok ? c.nok : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1 text-xs text-text-secondary">
        Número = {countLabel}; tono proporcional a la tasa (máx. {formatPct(max)}, recuadrada).
      </p>
    </div>
  );
}
