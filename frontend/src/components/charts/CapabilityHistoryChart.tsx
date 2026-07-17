import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CapabilityWindow } from "../../lib/live-monitor/types";

// LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md): one bar per real F8.D
// window (see backend/app/services/capability_history_service.py) --
// dataviz skill: single-series magnitude, so status color (not a
// categorical hue) carries the "capable / marginal / not capable" state,
// same semantics as the 1.33 threshold already used in SignalDetailPanel.
const CAPABLE_THRESHOLD = 1.33;
const MARGINAL_THRESHOLD = 1.0;

function statusColorForCpk(cpkValue: number | null): string {
  if (cpkValue === null) return "var(--status-neutral)";
  if (cpkValue >= CAPABLE_THRESHOLD) return "var(--status-ok)";
  if (cpkValue >= MARGINAL_THRESHOLD) return "var(--status-warning)";
  return "var(--status-nok)";
}

interface ChartDatum {
  label: string;
  cpk: number | null;
  pointCount: number;
  windowStart: string;
  windowEnd: string;
}

function formatWindowLabel(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function CapabilityTooltip({ active, payload }: { active?: boolean; payload?: { payload: ChartDatum }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div
      className="rounded border px-3 py-2 text-xs"
      style={{
        background: "var(--bg-surface-raised)",
        border: "1px solid var(--border-default)",
        color: "var(--text-primary)",
      }}
    >
      <p className="font-medium">
        {formatWindowLabel(point.windowStart)} – {formatWindowLabel(point.windowEnd)}
      </p>
      <p className="mt-0.5 text-text-secondary">{point.pointCount} points</p>
      <p className="mt-0.5">Cpk {point.cpk !== null ? point.cpk.toFixed(2) : "undefined"}</p>
    </div>
  );
}

export function CapabilityHistoryChart({ windows }: { windows: CapabilityWindow[] }) {
  const data: ChartDatum[] = windows.map((w) => ({
    label: formatWindowLabel(w.window_end),
    cpk: w.cpk !== null ? Number(w.cpk) : null,
    pointCount: w.point_count,
    windowStart: w.window_start,
    windowEnd: w.window_end,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: "var(--text-secondary)" }} tickLine={false} width={32} />
        <ReferenceLine
          y={CAPABLE_THRESHOLD}
          stroke="var(--status-ok)"
          strokeDasharray="4 3"
          label={{ value: `${CAPABLE_THRESHOLD}`, position: "right", fontSize: 11, fill: "var(--status-ok)" }}
        />
        <Tooltip content={<CapabilityTooltip />} />
        <Bar dataKey="cpk" radius={[4, 4, 0, 0]} isAnimationActive={false}>
          {data.map((d) => (
            <Cell key={`${d.windowStart}-${d.windowEnd}`} fill={statusColorForCpk(d.cpk)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
