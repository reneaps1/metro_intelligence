import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CategoricalChartState } from "recharts/types/chart/types";
import {
  formatRelative,
  formatValue,
  isStepSignal,
  type CursorId,
  type TimeWindow,
  type Trace,
} from "../../lib/industrial-signals/explorer";
import type { ProcessEvent, SignalSeries } from "../../lib/industrial-signals/types";

// IQ-F3: one chart sharing the explorer's time axis. In "tracks" layout it
// holds one unit; in "overlay" layout it gets one Y axis per unit, so curves
// in °C and bar never share a scale.

const SEVERITY_COLOR: Record<ProcessEvent["severity"], string> = {
  info: "var(--status-info)",
  warning: "var(--status-warning)",
  critical: "var(--status-nok)",
};

const CURSOR_COLOR: Record<CursorId, string> = { a: "var(--brand-primary)", b: "var(--chart-4)" };

interface TrackChartProps {
  title: string;
  traces: Trace[];
  seriesById: Record<string, SignalSeries>;
  window: TimeWindow;
  origin: number;
  cursors: Record<CursorId, number | null>;
  events: ProcessEvent[];
  showEventLabels: boolean;
  height: number;
  onZoom: (window: TimeWindow) => void;
  onCursor: (time: number) => void;
}

type Row = { t: number } & Record<string, number | undefined>;

export function TrackChart({
  title,
  traces,
  seriesById,
  window,
  origin,
  cursors,
  events,
  showEventLabels,
  height,
  onZoom,
  onCursor,
}: TrackChartProps) {
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const span = window.end - window.start;
  const withSeconds = span < 3_600_000;

  const visible = traces.filter((t) => t.visible);
  const units = [...new Set(visible.map((t) => t.signal.unit))];

  const data = useMemo(() => {
    const rows = new Map<number, Row>();
    for (const trace of visible) {
      const series = seriesById[trace.signal.signal_id];
      if (!series) continue;
      for (const [t, v] of series.points) {
        if (t < window.start || t > window.end) continue;
        const row = rows.get(t) ?? ({ t } as Row);
        row[trace.signal.signal_id] = v;
        rows.set(t, row);
      }
    }
    return [...rows.values()].sort((a, b) => a.t - b.t);
  }, [visible, seriesById, window.start, window.end]);

  function label(state: CategoricalChartState): number | null {
    const value = state?.activeLabel as unknown;
    return typeof value === "number" ? value : null;
  }

  function finishDrag() {
    if (dragStart !== null && dragEnd !== null && Math.abs(dragEnd - dragStart) > span * 0.01) {
      onZoom({ start: Math.min(dragStart, dragEnd), end: Math.max(dragStart, dragEnd) });
    } else if (dragStart !== null) {
      onCursor(dragStart);
    }
    setDragStart(null);
    setDragEnd(null);
  }

  // Short "E<n>" markers (numbered like the event list) instead of full
  // labels, which overlap as soon as two events are close together.
  const windowEvents = events
    .map((event, index) => ({ event, marker: `E${index + 1}` }))
    .filter(({ event }) => {
      const start = Date.parse(event.start);
      const end = event.end ? Date.parse(event.end) : start;
      return end >= window.start && start <= window.end;
    });

  return (
    <figure className="rounded border border-border bg-surface-app p-2" aria-label={`Pista ${title}`}>
      <figcaption className="mb-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        <span className="font-semibold text-text-primary">{title}</span>
        {visible.map((trace) => (
          <span key={trace.signal.signal_id} className="inline-flex items-center gap-1 text-text-secondary">
            <span className="inline-block h-2 w-3 rounded-sm" style={{ background: trace.color }} aria-hidden="true" />
            {trace.signal.machine_code} · {trace.signal.name}
          </span>
        ))}
      </figcaption>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={data}
          syncId="iiot-explorer"
          syncMethod="value"
          margin={{ top: 6, right: units.length > 1 ? 8 : 16, bottom: 0, left: 0 }}
          onMouseDown={(state) => {
            const t = label(state);
            if (t === null) return;
            setDragStart(t);
            setDragEnd(t);
          }}
          onMouseMove={(state) => {
            if (dragStart === null) return;
            const t = label(state);
            if (t !== null) setDragEnd(t);
          }}
          onMouseUp={finishDrag}
          onMouseLeave={() => {
            setDragStart(null);
            setDragEnd(null);
          }}
          style={{ cursor: "crosshair", userSelect: "none" }}
        >
          <CartesianGrid stroke="var(--border-default)" strokeOpacity={0.5} />
          <XAxis
            dataKey="t"
            type="number"
            domain={[window.start, window.end]}
            allowDataOverflow
            tickFormatter={(t: number) => formatRelative(t, origin, withSeconds)}
            tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
            minTickGap={40}
          />
          {units.map((unit, i) => (
            <YAxis
              key={unit}
              yAxisId={unit}
              orientation={i % 2 === 0 ? "left" : "right"}
              domain={["auto", "auto"]}
              width={58}
              tick={{ fontSize: 11, fill: "var(--text-secondary)" }}
              tickFormatter={(v: number) => formatValue(v)}
              label={{ value: unit, angle: -90, position: i % 2 === 0 ? "insideLeft" : "insideRight", fontSize: 11, fill: "var(--text-secondary)" }}
            />
          ))}
          <Tooltip
            isAnimationActive={false}
            labelFormatter={(t: number) => formatRelative(t, origin, true)}
            formatter={(value: number, name: string) => {
              const trace = visible.find((tr) => tr.signal.signal_id === name);
              return [`${formatValue(value)} ${trace?.signal.unit ?? ""}`, trace?.signal.name ?? name];
            }}
            contentStyle={{
              background: "var(--bg-surface-raised)",
              border: "1px solid var(--border-default)",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          {windowEvents.map(({ event, marker }) => {
            const color = SEVERITY_COLOR[event.severity];
            const label = showEventLabels
              ? { value: marker, position: "insideTopLeft" as const, fontSize: 10, fontWeight: 600, fill: color }
              : undefined;
            return event.end ? (
              <ReferenceArea
                key={event.id}
                yAxisId={units[0]}
                x1={Math.max(Date.parse(event.start), window.start)}
                x2={Math.min(Date.parse(event.end), window.end)}
                fill={color}
                fillOpacity={0.1}
                ifOverflow="hidden"
                label={label}
              />
            ) : (
              <ReferenceLine
                key={event.id}
                yAxisId={units[0]}
                x={Date.parse(event.start)}
                stroke={color}
                strokeDasharray="3 3"
                label={label}
              />
            );
          })}
          {visible.map((trace) => (
            <Line
              key={trace.signal.signal_id}
              yAxisId={trace.signal.unit}
              dataKey={trace.signal.signal_id}
              name={trace.signal.signal_id}
              stroke={trace.color}
              strokeWidth={1.5}
              dot={false}
              type={isStepSignal(trace.signal) ? "stepAfter" : "linear"}
              connectNulls
              isAnimationActive={false}
            />
          ))}
          {(["a", "b"] as const).map((id) =>
            cursors[id] !== null && cursors[id]! >= window.start && cursors[id]! <= window.end ? (
              <ReferenceLine
                key={id}
                yAxisId={units[0]}
                x={cursors[id]!}
                stroke={CURSOR_COLOR[id]}
                strokeWidth={1.5}
                label={{ value: id.toUpperCase(), position: "top", fontSize: 11, fill: CURSOR_COLOR[id] }}
              />
            ) : null,
          )}
          {dragStart !== null && dragEnd !== null && dragStart !== dragEnd && (
            <ReferenceArea
              yAxisId={units[0]}
              x1={Math.min(dragStart, dragEnd)}
              x2={Math.max(dragStart, dragEnd)}
              fill="var(--brand-primary)"
              fillOpacity={0.12}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </figure>
  );
}
