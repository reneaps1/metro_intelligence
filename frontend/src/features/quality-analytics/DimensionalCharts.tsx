import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatPct } from "../../lib/quality-analytics/filters";
import type { GroupBox, VariableDetailResponse } from "../../lib/quality-analytics/types";
import { plantDay, plantMinute } from "../../lib/time/plantTime";

// IQ-F5: charts for the dimensional exploration step. Specification limits
// (LSL/USL, red dashed) and control limits (UCL/LCL, blue dotted) are drawn
// differently and labelled -- they answer different questions.

const axisTick = { fontSize: 11, fill: "var(--text-secondary)" };
const tooltipStyle = { background: "var(--bg-surface-raised)", border: "1px solid var(--border-default)", fontSize: 12 };
const fmt = (v: number) => v.toLocaleString("es-MX", { maximumFractionDigits: 4 });

function specLines(spec: VariableDetailResponse["spec"], axis: "x" | "y") {
  const lines = [];
  if (spec.lsl !== null) lines.push({ v: spec.lsl, label: "LSL" });
  if (spec.usl !== null) lines.push({ v: spec.usl, label: "USL" });
  return lines.map(({ v, label }) => (
    <ReferenceLine
      key={label}
      {...{ [axis]: v }}
      stroke="var(--status-nok)"
      strokeDasharray="4 3"
      ifOverflow="extendDomain"
      label={{ value: label, position: axis === "x" ? "top" : "right", fontSize: 10, fill: "var(--status-nok)" }}
    />
  ));
}

export function HistogramChart({ detail }: { detail: VariableDetailResponse }) {
  const data = detail.histogram.map((b) => ({ mid: (b.x0 + b.x1) / 2, count: b.count, range: `${fmt(b.x0)} – ${fmt(b.x1)}` }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 16, right: 16, bottom: 0, left: 0 }} barCategoryGap={1}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
        <XAxis dataKey="mid" type="number" domain={["dataMin", "dataMax"]} tick={axisTick} tickFormatter={fmt} />
        <YAxis tick={axisTick} width={44} allowDecimals={false} />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(v: number) => [v, "Piezas"]}
          labelFormatter={(_l, payload) => (payload?.[0]?.payload as { range?: string } | undefined)?.range ?? ""}
        />
        <Bar dataKey="count" fill="var(--chart-1)" isAnimationActive={false} />
        {specLines(detail.spec, "x")}
        {detail.spec.nominal !== null && (
          <ReferenceLine x={detail.spec.nominal} stroke="var(--text-secondary)" strokeDasharray="2 2" label={{ value: "Nom.", position: "top", fontSize: 10, fill: "var(--text-secondary)" }} />
        )}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function BoxplotChart({ groups, spec, label }: { groups: GroupBox[]; spec: VariableDetailResponse["spec"]; label: (g: string) => string }) {
  if (groups.length === 0) return <p className="text-sm text-text-secondary">Sin datos para este agrupamiento.</p>;
  const lows = [...groups.map((g) => g.whisker_low), ...(spec.lsl !== null ? [spec.lsl] : [])];
  const highs = [...groups.map((g) => g.whisker_high), ...(spec.usl !== null ? [spec.usl] : [])];
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const pad = (max - min) * 0.08 || 1;
  const lo = min - pad;
  const hi = max + pad;
  // Wider than the card when there are many groups (e.g. 32 mold cavities): scroll instead of squeezing labels.
  const W = Math.max(640, groups.length * 26);
  const H = 240;
  const left = 56;
  const bottom = 28;
  const plotH = H - bottom - 8;
  const y = (v: number) => 8 + ((hi - v) / (hi - lo)) * plotH;
  const step = (W - left - 8) / groups.length;
  const boxW = Math.min(36, step * 0.6);
  const ticks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) * i) / 4);

  return (
    <div className="overflow-x-auto">
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: W > 640 ? W : undefined }} role="img" aria-label="Diagrama de caja por grupo">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={left} x2={W - 8} y1={y(t)} y2={y(t)} stroke="var(--border-default)" strokeOpacity={0.5} />
          <text x={left - 4} y={y(t) + 3} textAnchor="end" fontSize={10} fill="var(--text-secondary)">
            {fmt(t)}
          </text>
        </g>
      ))}
      {[
        { v: spec.lsl, l: "LSL" },
        { v: spec.usl, l: "USL" },
      ].map(({ v, l }) =>
        v === null ? null : (
          <g key={l}>
            <line x1={left} x2={W - 8} y1={y(v)} y2={y(v)} stroke="var(--status-nok)" strokeDasharray="4 3" />
            <text x={W - 10} y={y(v) - 3} textAnchor="end" fontSize={10} fill="var(--status-nok)">
              {l}
            </text>
          </g>
        ),
      )}
      {groups.map((g, i) => {
        const cx = left + step * i + step / 2;
        const highlight = g.nok_rate > 0.05;
        return (
          <g key={g.group}>
            <title>
              {`${label(g.group)} · n=${g.n} · mediana ${fmt(g.median)} · Q1–Q3 ${fmt(g.q1)}–${fmt(g.q3)} · NOK ${formatPct(g.nok_rate)}`}
            </title>
            <line x1={cx} x2={cx} y1={y(g.whisker_high)} y2={y(g.q3)} stroke="var(--text-secondary)" />
            <line x1={cx} x2={cx} y1={y(g.q1)} y2={y(g.whisker_low)} stroke="var(--text-secondary)" />
            <line x1={cx - boxW / 4} x2={cx + boxW / 4} y1={y(g.whisker_high)} y2={y(g.whisker_high)} stroke="var(--text-secondary)" />
            <line x1={cx - boxW / 4} x2={cx + boxW / 4} y1={y(g.whisker_low)} y2={y(g.whisker_low)} stroke="var(--text-secondary)" />
            <rect
              x={cx - boxW / 2}
              y={y(g.q3)}
              width={boxW}
              height={Math.max(1, y(g.q1) - y(g.q3))}
              fill={highlight ? "var(--status-nok-bg)" : "var(--status-info-bg)"}
              stroke={highlight ? "var(--status-nok)" : "var(--chart-1)"}
            />
            <line x1={cx - boxW / 2} x2={cx + boxW / 2} y1={y(g.median)} y2={y(g.median)} stroke="var(--text-primary)" strokeWidth={2} />
            <text x={cx} y={H - 10} textAnchor="middle" fontSize={10} fill="var(--text-secondary)">
              {label(g.group)}
            </text>
          </g>
        );
      })}
    </svg>
    </div>
  );
}

export function IndividualsChart({ detail, offsetMinutes = 0 }: { detail: VariableDetailResponse; offsetMinutes?: number }) {
  const ok = detail.series.filter((p) => !p[2]).map(([t, v]) => ({ t, v }));
  const nok = detail.series.filter((p) => p[2]).map(([t, v]) => ({ t, v }));
  const cl = detail.control_limits;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ top: 8, right: 40, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
        <XAxis
          dataKey="t"
          type="number"
          domain={["dataMin", "dataMax"]}
          tick={axisTick}
          tickFormatter={(t: number) => plantDay(t, offsetMinutes)}
        />
        <YAxis dataKey="v" type="number" domain={["auto", "auto"]} tick={axisTick} width={56} tickFormatter={fmt} />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(v: number, name: string) => (name === "t" ? [plantMinute(v, offsetMinutes), "Hora"] : [fmt(v), detail.spec.unit])}
        />
        <Scatter data={ok} fill="var(--chart-1)" fillOpacity={0.35} isAnimationActive={false} shape="circle" />
        <Scatter data={nok} fill="var(--status-nok)" isAnimationActive={false} shape="triangle" />
        {specLines(detail.spec, "y")}
        {cl && (
          <>
            <ReferenceLine y={cl.center_line} stroke="var(--chart-2)" strokeDasharray="6 3" label={{ value: "CL", position: "right", fontSize: 10, fill: "var(--chart-2)" }} />
            <ReferenceLine y={cl.ucl} stroke="var(--chart-2)" strokeDasharray="1 3" label={{ value: "UCL", position: "right", fontSize: 10, fill: "var(--chart-2)" }} />
            <ReferenceLine y={cl.lcl} stroke="var(--chart-2)" strokeDasharray="1 3" label={{ value: "LCL", position: "right", fontSize: 10, fill: "var(--chart-2)" }} />
          </>
        )}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function DailyCpkChart({ detail }: { detail: VariableDetailResponse }) {
  const data = detail.cpk_by_day.map((d) => ({ ...d, label: d.day.slice(5) }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 40, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
        <XAxis dataKey="label" tick={axisTick} />
        <YAxis tick={axisTick} width={40} domain={[0, "auto"]} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number, _n, item: { payload?: { n: number } }) => [`${v.toFixed(2)} (n=${item.payload?.n ?? 0})`, "Cpk"]} />
        <ReferenceLine y={1.33} stroke="var(--status-ok)" strokeDasharray="4 3" label={{ value: "1.33", position: "right", fontSize: 10, fill: "var(--status-ok)" }} />
        <ReferenceLine y={1} stroke="var(--status-warning)" strokeDasharray="4 3" label={{ value: "1.00", position: "right", fontSize: 10, fill: "var(--status-warning)" }} />
        <Line dataKey="cpk" stroke="var(--chart-3)" strokeWidth={2} connectNulls isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
