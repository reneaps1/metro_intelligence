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
import { WB, axisTick, gridProps, tooltipStyle } from "../../lib/demo/chartTheme";
import {
  formatRelative,
  formatValue,
  isStepSignal,
  type CursorId,
  type TimeWindow,
  type Trace,
} from "../../lib/industrial-signals/explorer";
import type { ProcessEvent, SignalSeries } from "../../lib/industrial-signals/types";
import { LpSymbol } from "../line-panel/parts";

// IQ-F3: one chart sharing the explorer's time axis. In "tracks" layout it
// holds one unit; in "overlay" layout it gets one Y axis per unit, so curves
// in °C and bar never share a scale. IQ-F16: each pen keeps its categorical
// --chart-* color (each one is a different signal); the chrome around them is
// neutral -- event markers and cursors in the text color, the zoom selection in
// the teal "selected" tint, and only warning/critical events carry their
// priority symbol (line panel's LpSymbol) next to the marker.

// Cursor A solid, cursor B dashed: told apart by line and label, not by hue.
const CURSOR_DASH: Record<CursorId, string | undefined> = { a: undefined, b: "6 3" };

// Recharts label content for an event marker: "E<n>", preceded by the priority
// symbol when the event asks for attention (warning -> P2, critical -> P1).
function EventMarker({
  viewBox,
  marker,
  severity,
}: {
  viewBox?: { x: number; y: number };
  marker: string;
  severity: ProcessEvent["severity"];
}) {
  if (!viewBox) return null;
  const x = viewBox.x + 3;
  const y = viewBox.y + 3;
  const symbol = severity === "info" ? null : severity === "critical" ? 1 : 2;
  return (
    <g pointerEvents="none">
      {symbol !== null && (
        <g transform={`translate(${x},${y})`}>
          <LpSymbol priority={symbol} size={12} />
        </g>
      )}
      <text x={x + (symbol !== null ? 15 : 0)} y={y + 10} fontSize={10} fontWeight={700} fill={WB.ref}>
        {marker}
      </text>
    </g>
  );
}

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
    <figure className="overflow-hidden rounded-md border border-border bg-surface" aria-label={`Pista ${title}`}>
      <figcaption className="flex min-h-[32px] flex-wrap items-center gap-x-3 gap-y-1 border-b border-border bg-wb-pane-header px-3 py-1 text-xs">
        <span className="wb-label">{title}</span>
        {visible.map((trace) => (
          <span key={trace.signal.signal_id} className="inline-flex items-center gap-1.5 font-medium text-text-primary">
            <span className="inline-block h-[3px] w-4 rounded-sm" style={{ background: trace.color }} aria-hidden="true" />
            {trace.signal.machine_code} · {trace.signal.name}
          </span>
        ))}
      </figcaption>
      <div className="p-2">
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
          <CartesianGrid {...gridProps} />
          <XAxis
            dataKey="t"
            type="number"
            domain={[window.start, window.end]}
            allowDataOverflow
            tickFormatter={(t: number) => formatRelative(t, origin, withSeconds)}
            tick={axisTick}
            minTickGap={40}
          />
          {units.map((unit, i) => (
            <YAxis
              key={unit}
              yAxisId={unit}
              orientation={i % 2 === 0 ? "left" : "right"}
              domain={["auto", "auto"]}
              width={58}
              tick={axisTick}
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
            contentStyle={tooltipStyle}
          />
          {windowEvents.map(({ event, marker }) => {
            const label = showEventLabels ? <EventMarker marker={marker} severity={event.severity} /> : undefined;
            return event.end ? (
              <ReferenceArea
                key={event.id}
                yAxisId={units[0]}
                x1={Math.max(Date.parse(event.start), window.start)}
                x2={Math.min(Date.parse(event.end), window.end)}
                fill={WB.mark}
                fillOpacity={0.08}
                ifOverflow="hidden"
                label={label}
              />
            ) : (
              <ReferenceLine
                key={event.id}
                yAxisId={units[0]}
                x={Date.parse(event.start)}
                stroke={WB.text}
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
                stroke={WB.ref}
                strokeWidth={1.5}
                strokeDasharray={CURSOR_DASH[id]}
                label={{ value: id.toUpperCase(), position: "top", fontSize: 11, fontWeight: 700, fill: WB.ref }}
              />
            ) : null,
          )}
          {dragStart !== null && dragEnd !== null && dragStart !== dragEnd && (
            <ReferenceArea
              yAxisId={units[0]}
              x1={Math.min(dragStart, dragEnd)}
              x2={Math.max(dragStart, dragEnd)}
              fill="var(--brand-accent)"
              fillOpacity={0.14}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      </div>
    </figure>
  );
}
