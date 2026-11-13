import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatDay } from "../../lib/process/format";
import type { CharacteristicDailyPoint, DailyCount, HistogramBin, SpecLimits, StepOverview } from "../../lib/process/types";

// Chart styling follows docs/design/design-system.md: token colors only,
// gridlines at 50 % border, tolerance limits dashed in the NOK color, no
// animation, labelled units.
const GRID = { stroke: "var(--border-default)", strokeOpacity: 0.5 };
const TICK = { fontSize: 11, fill: "var(--text-secondary)" };
const TOOLTIP_STYLE = {
  background: "var(--bg-surface-raised)",
  border: "1px solid var(--border-default)",
  borderRadius: 6,
  fontSize: 12,
};
const SERIES = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)"];

/** Pieces per day split into OK and NOK (stacked), for one step. */
export function DailyPiecesChart({ trend, useSpec }: { trend: DailyCount[]; useSpec: boolean }) {
  const data = trend.map((d) => {
    const nok = useSpec ? d.spec_nok : d.machine_nok;
    return { day: formatDay(d.day), ok: d.pieces - nok, nok };
  });
  const nokLabel = useSpec ? "Out of drawing tolerance" : "Station NOK";
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid {...GRID} vertical={false} />
        <XAxis dataKey="day" tick={TICK} tickLine={false} minTickGap={16} />
        <YAxis tick={TICK} tickLine={false} width={56} allowDecimals={false} label={{ value: "pieces", angle: -90, position: "insideLeft", style: TICK }} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="ok" name="OK" stackId="pieces" fill="var(--status-ok)" isAnimationActive={false} />
        <Bar dataKey="nok" name={nokLabel} stackId="pieces" fill="var(--status-nok)" isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** NOK rate per day, one series per step in process order. Straight
 * segments between days: nothing is invented between two measurements. */
export function StepNokTrendChart({ steps }: { steps: StepOverview[] }) {
  const ordered = [...steps].sort((a, b) => a.operation.sequence - b.operation.sequence);
  const days = new Map<string, Record<string, number | string>>();
  for (const step of ordered) {
    for (const d of step.trend) {
      const row = days.get(d.day) ?? { day: d.day };
      const nok = step.has_specification ? d.spec_nok : d.machine_nok;
      row[step.operation.code] = d.pieces ? (nok / d.pieces) * 100 : 0;
      days.set(d.day, row);
    }
  }
  const data = [...days.values()]
    .sort((a, b) => String(a.day).localeCompare(String(b.day)))
    .map((row) => ({ ...row, label: formatDay(String(row.day)) }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid {...GRID} vertical={false} />
        <XAxis dataKey="label" tick={TICK} tickLine={false} minTickGap={16} />
        <YAxis tick={TICK} tickLine={false} width={48} unit="%" />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value: number) => `${value.toFixed(2)}%`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {ordered.map((step, i) => (
          <Line
            key={step.operation.id}
            type="linear"
            dataKey={step.operation.code}
            name={step.operation.name}
            stroke={SERIES[i % SERIES.length]}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

function limitNumbers(spec: SpecLimits | null): { lower: number | null; upper: number | null } {
  return {
    lower: spec?.lower_limit != null ? Number(spec.lower_limit) : null,
    upper: spec?.upper_limit != null ? Number(spec.upper_limit) : null,
  };
}

/** Value distribution; bins beyond the drawing limits are drawn in the NOK color. */
export function ValueHistogram({ bins, spec, unit }: { bins: HistogramBin[]; spec: SpecLimits | null; unit: string }) {
  const { lower, upper } = limitNumbers(spec);
  const data = bins.map((b) => ({
    label: b.lower.toFixed(3),
    range: `${b.lower.toFixed(3)} – ${b.upper.toFixed(3)} ${unit}`,
    count: b.count,
    outside: (upper !== null && b.lower >= upper) || (lower !== null && b.upper <= lower),
  }));
  const binFor = (limit: number | null) => {
    if (limit === null) return undefined;
    const bin = bins.find((b) => limit >= b.lower && limit <= b.upper);
    return bin ? bin.lower.toFixed(3) : undefined;
  };
  const lowerBin = binFor(lower);
  const upperBin = binFor(upper);

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid {...GRID} vertical={false} />
        <XAxis dataKey="label" tick={TICK} tickLine={false} minTickGap={12} label={{ value: unit, position: "insideBottomRight", offset: -4, style: TICK }} />
        <YAxis tick={TICK} tickLine={false} width={56} allowDecimals={false} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          labelFormatter={(_, payload) => (payload?.[0]?.payload as { range?: string } | undefined)?.range ?? ""}
        />
        <Bar dataKey="count" name="Values" isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={d.label} fill={d.outside ? "var(--status-nok)" : "var(--chart-2)"} />
          ))}
        </Bar>
        {lowerBin && <ReferenceLine x={lowerBin} stroke="var(--status-nok)" strokeDasharray="4 4" label={{ value: "LSL", fill: "var(--status-nok)", fontSize: 11, position: "top" }} />}
        {upperBin && <ReferenceLine x={upperBin} stroke="var(--status-nok)" strokeDasharray="4 4" label={{ value: "USL", fill: "var(--status-nok)", fontSize: 11, position: "top" }} />}
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Daily mean with the daily min–max band and the drawing limits. */
export function DailyMeanChart({ daily, spec, unit }: { daily: CharacteristicDailyPoint[]; spec: SpecLimits | null; unit: string }) {
  const { lower, upper } = limitNumbers(spec);
  const data = daily.map((d) => ({ day: formatDay(d.day), mean: d.mean, band: [d.min, d.max] as [number, number], nok: d.spec_nok }));
  // Scale to the means and limits, not to the extremes: a single gross
  // outlier (a mis-read pin) would otherwise flatten the trend. The band is
  // clipped at the chart edge instead.
  const anchors = [...daily.map((d) => d.mean), ...(lower !== null ? [lower] : []), ...(upper !== null ? [upper] : [])];
  const lo = Math.min(...anchors);
  const hi = Math.max(...anchors);
  const pad = (hi - lo || Math.abs(hi) || 1) * 0.25;
  const domain: [number, number] = [lo - pad, hi + pad];
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid {...GRID} vertical={false} />
        <XAxis dataKey="day" tick={TICK} tickLine={false} minTickGap={16} />
        <YAxis tick={TICK} tickLine={false} width={64} domain={domain} allowDataOverflow tickFormatter={(v: number) => v.toFixed(3)} label={{ value: unit, angle: -90, position: "insideLeft", style: TICK }} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(value: number | [number, number]) => (Array.isArray(value) ? `${value[0].toFixed(3)} – ${value[1].toFixed(3)}` : value.toFixed(4))} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area dataKey="band" name="Daily min – max" fill="var(--chart-2)" fillOpacity={0.15} stroke="none" isAnimationActive={false} />
        <Line dataKey="mean" name="Daily mean" stroke="var(--chart-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
        {lower !== null && <ReferenceLine y={lower} stroke="var(--status-nok)" strokeDasharray="4 4" label={{ value: "LSL", fill: "var(--status-nok)", fontSize: 11, position: "insideBottomLeft" }} />}
        {upper !== null && <ReferenceLine y={upper} stroke="var(--status-nok)" strokeDasharray="4 4" label={{ value: "USL", fill: "var(--status-nok)", fontSize: 11, position: "insideTopLeft" }} />}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
