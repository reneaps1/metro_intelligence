import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { MeasurementPoint, Specification } from "../../lib/mock/types";

interface TrendChartProps {
  points: MeasurementPoint[];
  specification: Specification;
  unit: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function CustomDot(props: { cx?: number; cy?: number; payload?: MeasurementPoint }) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined || !payload) return null;
  if (payload.isOk) {
    return <circle cx={cx} cy={cy} r={3} fill="var(--chart-1)" stroke="none" />;
  }
  // NOK points get a distinct shape (triangle), not just a color change.
  const size = 6;
  const points = `${cx},${cy - size} ${cx - size},${cy + size} ${cx + size},${cy + size}`;
  return <polygon points={points} fill="var(--status-nok)" />;
}

export function TrendChart({ points, specification, unit }: TrendChartProps) {
  const data = points.map((p) => ({ ...p, label: formatDate(p.measuredAt) }));
  const upperLimit = specification.upperTol !== null ? specification.upperTol : undefined;
  const lowerLimit = specification.lowerTol !== null ? specification.lowerTol : undefined;

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 48, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} tickLine={false} />
          <YAxis
            tick={{ fontSize: 12, fill: "var(--text-secondary)" }}
            tickLine={false}
            width={56}
            label={{ value: `deviation (${unit})`, angle: -90, position: "insideLeft", fill: "var(--text-secondary)", fontSize: 12 }}
          />
          <Tooltip
            contentStyle={{ background: "var(--bg-surface-raised)", border: "1px solid var(--border-default)", borderRadius: 6, fontSize: 12 }}
            formatter={(value: number) => [`${value.toFixed(4)} ${unit}`, "Deviation"]}
          />
          <ReferenceLine y={0} stroke="var(--text-secondary)" strokeDasharray="4 4" label={{ value: "Nominal", position: "right", fontSize: 11, fill: "var(--text-secondary)" }} />
          {upperLimit !== undefined && (
            <ReferenceLine y={upperLimit} stroke="var(--status-nok)" strokeDasharray="2 2" label={{ value: "USL", position: "right", fontSize: 11, fill: "var(--status-nok)" }} />
          )}
          {lowerLimit !== undefined && (
            <ReferenceLine y={lowerLimit} stroke="var(--status-nok)" strokeDasharray="2 2" label={{ value: "LSL", position: "right", fontSize: 11, fill: "var(--status-nok)" }} />
          )}
          <Line
            type="monotone"
            dataKey="deviation"
            stroke="var(--chart-1)"
            strokeWidth={2}
            dot={<CustomDot />}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-1 text-xs text-text-secondary">
        Individual measurements (I-MR). Triangles mark NOK results; dashed red lines are the tolerance limits, dashed gray is nominal.
      </p>
    </div>
  );
}
