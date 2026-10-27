import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  ErrorBar,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPct } from "../../lib/quality-analytics/filters";
import type { CavityRate, HeatmapCell, ParetoRow, QualityVariable, TrendBucket } from "../../lib/quality-analytics/types";

// IQ-F5: charts for the quality diagnosis step. Rates are shown in %, always
// next to their denominator (pieces) in tooltips.

const axisTick = { fontSize: 11, fill: "var(--text-secondary)" };
const tooltipStyle = {
  background: "var(--bg-surface-raised)",
  border: "1px solid var(--border-default)",
  borderRadius: 6,
  fontSize: 12,
};

export function NokTrendChart({ trend }: { trend: TrendBucket[] }) {
  const data = trend.map((b) => ({ ...b, pct: b.rate === null ? null : b.rate * 100, label: b.bucket.replace("T", " ") }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
        <XAxis dataKey="label" tick={axisTick} minTickGap={24} />
        <YAxis tick={axisTick} width={48} unit=" %" />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(_v: number, _n: string, item: { payload?: TrendBucket }) => [
            `${formatPct(item.payload?.rate ?? null)} (${item.payload?.nok ?? 0} / ${item.payload?.pieces ?? 0} piezas)`,
            "Tasa NOK",
          ]}
        />
        <Line dataKey="pct" stroke="var(--status-nok)" strokeWidth={2} dot={data.length < 40} isAnimationActive={false} />
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
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
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
        <Bar yAxisId="count" dataKey="nok" fill="var(--chart-1)" isAnimationActive={false} />
        <Line yAxisId="pct" dataKey="cumulative" stroke="var(--chart-4)" strokeWidth={2} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function CavityRateChart({ rows, worst }: { rows: CavityRate[]; worst: number | null }) {
  const data = rows.map((r) => ({
    ...r,
    label: `N${r.cavity}`,
    pct: r.rate === null ? 0 : r.rate * 100,
    ci:
      r.rate === null || r.ci_low === null || r.ci_high === null
        ? [0, 0]
        : [(r.rate - r.ci_low) * 100, (r.ci_high - r.rate) * 100],
  }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
        <XAxis dataKey="label" tick={axisTick} interval={0} />
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
            <Cell key={d.cavity} fill={d.cavity === worst ? "var(--status-nok)" : "var(--chart-1)"} />
          ))}
          <ErrorBar dataKey="ci" width={4} stroke="var(--text-secondary)" />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CavityHeatmap({ cells, variables }: { cells: HeatmapCell[]; variables: QualityVariable[] }) {
  const cavities = [...new Set(cells.map((c) => c.cavity))].sort((a, b) => a - b);
  const keys = [...new Set(cells.map((c) => c.variable))];
  const max = Math.max(...cells.map((c) => c.rate ?? 0), 0);
  const name = (key: string) => variables.find((v) => v.key === key)?.name ?? key;
  const cell = (cav: number, key: string) => cells.find((c) => c.cavity === cav && c.variable === key);
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-0.5 text-xs" aria-label="Mapa de calor nido por cota">
        <thead>
          <tr>
            <th className="sticky left-0 bg-surface px-1 text-left font-medium text-text-secondary">Cota \ Nido</th>
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
                const intensity = max > 0 && c?.rate ? Math.round((c.rate / max) * 85) + 10 : 0;
                return (
                  <td
                    key={cav}
                    title={`${name(key)} · nido ${cav}: ${c?.nok ?? 0} NOK / ${c?.pieces ?? 0} piezas (${formatPct(c?.rate ?? null)})`}
                    className="h-7 min-w-[34px] rounded-sm text-center font-mono text-[10px] text-text-primary"
                    style={{
                      background: intensity
                        ? `color-mix(in srgb, var(--status-nok) ${intensity}%, transparent)`
                        : "var(--bg-app)",
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
        Número = mediciones NOK de esa cota en ese nido; color proporcional a la tasa (máx. {formatPct(max)}).
      </p>
    </div>
  );
}
