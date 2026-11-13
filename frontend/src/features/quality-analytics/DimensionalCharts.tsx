import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
import { WB, axisTick, gridProps, limitLine, lineLabel, refLine, tooltipStyle } from "../../lib/demo/chartTheme";
import { formatPct } from "../../lib/quality-analytics/filters";
import type { GroupBox, VariableDetailResponse } from "../../lib/quality-analytics/types";
import { plantDay, plantMinute } from "../../lib/time/plantTime";

// IQ-F5: charts for the dimensional exploration step. Specification limits
// (LSL/USL) and control limits (UCL/LCL) are drawn differently and labelled --
// they answer different questions. IQ-F16: workbench chart theme -- neutral
// marks, limits in the text color (specification dashed, control dotted), and
// the muted NOK accent only for what falls outside: NOK pieces, out-of-control
// points, outliers and the group with the highest NOK rate.

const fmt = (v: number) => v.toLocaleString("es-MX", { maximumFractionDigits: 4 });

function specLines(spec: VariableDetailResponse["spec"], axis: "x" | "y") {
  const lines = [];
  if (spec.lsl !== null) lines.push({ v: spec.lsl, label: "LSL" });
  if (spec.usl !== null) lines.push({ v: spec.usl, label: "USL" });
  return lines.map(({ v, label }) => (
    <ReferenceLine
      key={label}
      {...{ [axis]: v }}
      {...limitLine}
      ifOverflow="extendDomain"
      label={axis === "x" ? { ...lineLabel(label), position: "top" } : lineLabel(label)}
    />
  ));
}

export function HistogramChart({ detail }: { detail: VariableDetailResponse }) {
  const { lsl, usl } = detail.spec;
  const data = detail.histogram.map((b) => {
    const mid = (b.x0 + b.x1) / 2;
    return {
      mid,
      count: b.count,
      range: `${fmt(b.x0)} – ${fmt(b.x1)}`,
      outside: (lsl !== null && mid < lsl) || (usl !== null && mid > usl),
    };
  });
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 18, right: 16, bottom: 0, left: 0 }} barCategoryGap={1}>
        <XAxis dataKey="mid" type="number" domain={["dataMin", "dataMax"]} tick={axisTick} tickFormatter={fmt} />
        <YAxis tick={axisTick} width={44} allowDecimals={false} />
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(v: number) => [v, "Piezas"]}
          labelFormatter={(_l, payload) => (payload?.[0]?.payload as { range?: string } | undefined)?.range ?? ""}
        />
        <Bar dataKey="count" isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.mid} fill={d.outside ? WB.nok : WB.bar} />
          ))}
        </Bar>
        {specLines(detail.spec, "x")}
        {detail.spec.nominal !== null && (
          <ReferenceLine x={detail.spec.nominal} {...refLine} label={{ ...lineLabel("Nom."), position: "top" }} />
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
  // Same rule as step 2: only the group with the highest NOK rate is highlighted.
  const worstRate = Math.max(0, ...groups.map((g) => g.nok_rate));

  return (
    <div className="overflow-x-auto">
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ minWidth: W > 640 ? W : undefined }} role="img" aria-label="Diagrama de caja por grupo">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={left} x2={W - 8} y1={y(t)} y2={y(t)} stroke={WB.grid} strokeOpacity={0.35} />
          <text x={left - 4} y={y(t) + 3} textAnchor="end" fontSize={10} fill={WB.text}>
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
            <line x1={left} x2={W - 8} y1={y(v)} y2={y(v)} {...limitLine} />
            <text x={W - 10} y={y(v) - 4} textAnchor="end" fontSize={10} fontWeight={700} fill={WB.ref}>
              {l}
            </text>
          </g>
        ),
      )}
      {groups.map((g, i) => {
        const cx = left + step * i + step / 2;
        const highlight = worstRate > 0 && g.nok_rate === worstRate;
        // Only the extremes are known: draw them when they lie beyond the whiskers (clamped to the plot).
        const extremes = g.outliers > 0 ? [g.min < g.whisker_low ? g.min : null, g.max > g.whisker_high ? g.max : null] : [];
        return (
          <g key={g.group}>
            <title>
              {`${label(g.group)} · n=${g.n} · mediana ${fmt(g.median)} · Q1–Q3 ${fmt(g.q1)}–${fmt(g.q3)} · NOK ${formatPct(g.nok_rate)}${g.outliers ? ` · ${g.outliers} atípicos` : ""}`}
            </title>
            <line x1={cx} x2={cx} y1={y(g.whisker_high)} y2={y(g.q3)} stroke={WB.text} />
            <line x1={cx} x2={cx} y1={y(g.q1)} y2={y(g.whisker_low)} stroke={WB.text} />
            <line x1={cx - boxW / 4} x2={cx + boxW / 4} y1={y(g.whisker_high)} y2={y(g.whisker_high)} stroke={WB.text} />
            <line x1={cx - boxW / 4} x2={cx + boxW / 4} y1={y(g.whisker_low)} y2={y(g.whisker_low)} stroke={WB.text} />
            <rect
              x={cx - boxW / 2}
              y={y(g.q3)}
              width={boxW}
              height={Math.max(1, y(g.q1) - y(g.q3))}
              fill={highlight ? "var(--wb-nok-soft)" : WB.soft}
              stroke={highlight ? WB.nok : WB.bar}
              strokeWidth={highlight ? 1.5 : 1}
            />
            <line x1={cx - boxW / 2} x2={cx + boxW / 2} y1={y(g.median)} y2={y(g.median)} stroke={highlight ? WB.nok : WB.ref} strokeWidth={2} />
            {extremes.map((v, k) => {
              if (v === null) return null;
              const cy = y(Math.min(hi, Math.max(lo, v)));
              if (v >= lo && v <= hi) return <circle key={k} cx={cx} cy={cy} r={2.5} fill={WB.nok} />;
              const d = v > hi ? 6 : -6; // clamped: a caret pointing out of the plot
              return <path key={k} d={`M${cx - 4} ${cy + d} L${cx} ${cy} L${cx + 4} ${cy + d} Z`} fill={WB.nok} />;
            })}
            <text
              x={cx}
              y={H - 10}
              textAnchor="middle"
              fontSize={10}
              fontWeight={highlight ? 700 : 400}
              fill={highlight ? WB.nok : WB.text}
            >
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
  const cl = detail.control_limits;
  const outOfControl = (v: number) => cl !== null && (v > cl.ucl || v < cl.lcl);
  const ok = detail.series.filter((p) => !p[2] && !outOfControl(p[1])).map(([t, v]) => ({ t, v }));
  const ooc = detail.series.filter((p) => !p[2] && outOfControl(p[1])).map(([t, v]) => ({ t, v }));
  const nok = detail.series.filter((p) => p[2]).map(([t, v]) => ({ t, v }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ScatterChart margin={{ top: 8, right: 44, bottom: 0, left: 0 }}>
        <CartesianGrid {...gridProps} />
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
        <Scatter data={ok} fill={WB.bar} fillOpacity={0.45} isAnimationActive={false} shape="circle" />
        {/* Out of control: outlined, so the solid NOK triangles stay the strongest mark. */}
        {ooc.length > 0 && (
          <Scatter data={ooc} fill="transparent" stroke={WB.nok} strokeWidth={1.25} isAnimationActive={false} shape="circle" />
        )}
        <Scatter data={nok} fill={WB.nok} isAnimationActive={false} shape="triangle" />
        {specLines(detail.spec, "y")}
        {cl && (
          <>
            <ReferenceLine y={cl.center_line} {...refLine} stroke={WB.text} label={{ ...lineLabel("CL"), fill: WB.text }} />
            <ReferenceLine y={cl.ucl} {...refLine} label={lineLabel("UCL")} />
            <ReferenceLine y={cl.lcl} {...refLine} label={lineLabel("LCL")} />
          </>
        )}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

// A day below Cpk 1.00 (not capable) takes the NOK accent; the rest are neutral dots.
function CpkDot(props: { cx?: number; cy?: number; index?: number; payload?: { cpk: number | null } }) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined || payload?.cpk === null || payload?.cpk === undefined) return <g key={props.index} />;
  const low = payload.cpk < 1;
  return <circle key={props.index} cx={cx} cy={cy} r={low ? 3.5 : 2.5} fill={low ? WB.nok : WB.mark} stroke="none" />;
}

export function DailyCpkChart({ detail }: { detail: VariableDetailResponse }) {
  const data = detail.cpk_by_day.map((d) => ({ ...d, label: d.day.slice(5) }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 76, bottom: 0, left: 0 }}>
        <CartesianGrid {...gridProps} />
        <XAxis dataKey="label" tick={axisTick} />
        <YAxis tick={axisTick} width={40} domain={[0, "auto"]} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: number, _n, item: { payload?: { n: number } }) => [`${v.toFixed(2)} (n=${item.payload?.n ?? 0})`, "Cpk"]} />
        <ReferenceLine y={1.33} {...refLine} ifOverflow="extendDomain" label={lineLabel("Capaz 1.33")} />
        <ReferenceLine y={1} {...limitLine} ifOverflow="extendDomain" label={lineLabel("Mín. 1.00")} />
        <Line dataKey="cpk" stroke={WB.mark} strokeWidth={2} connectNulls dot={<CpkDot />} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
