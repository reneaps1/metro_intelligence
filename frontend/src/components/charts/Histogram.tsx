import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { histogramBins } from "../../lib/mock/analytics";
import type { MeasurementPoint, Specification } from "../../lib/mock/types";

export function Histogram({ points, specification }: { points: MeasurementPoint[]; specification: Specification }) {
  const bins = histogramBins(points);
  const data = bins.map((b) => ({ label: b.x0.toFixed(3), count: b.count }));
  const upperLimit = specification.upperTol !== null ? specification.nominal + specification.upperTol : undefined;
  const lowerLimit = specification.lowerTol !== null ? specification.nominal + specification.lowerTol : undefined;

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: "var(--text-secondary)" }} tickLine={false} width={32} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "var(--bg-surface-raised)", border: "1px solid var(--border-default)", borderRadius: 6, fontSize: 12 }}
        />
        <Bar dataKey="count" fill="var(--chart-2)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
        {lowerLimit !== undefined && <ReferenceLine x={lowerLimit.toFixed(3)} stroke="var(--status-nok)" strokeDasharray="2 2" />}
        {upperLimit !== undefined && <ReferenceLine x={upperLimit.toFixed(3)} stroke="var(--status-nok)" strokeDasharray="2 2" />}
      </BarChart>
    </ResponsiveContainer>
  );
}
