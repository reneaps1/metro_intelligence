import { useState } from "react";
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
import { ZoomOut } from "lucide-react";
import type { MeasurementPoint, Specification } from "../../lib/mock/types";
import { InfoTooltip } from "../ui/Tooltip";

// LM.2 (docs/tasks/LM2-live-monitor-detail-view.md): control limits are
// optional and expressed in the same deviation-space as the tolerance lines
// below (i.e. already offset from nominal by the caller) -- this component
// stays a "dumb" presentational chart and never computes them itself.
export interface ControlLimits {
  centerLine: number;
  ucl: number;
  lcl: number;
}

interface TrendChartProps {
  points: MeasurementPoint[];
  specification: Specification;
  unit: string;
  controlLimits?: ControlLimits | null;
  // Live Monitor deep-dive fix (2026-07): drag-to-zoom. Only the Live
  // Monitor detail page opts in -- SignalDetailPanel (LM.2's lighter panel)
  // and CharacteristicTrendPage (a separate, mock-data page) never pass this,
  // so they keep rendering exactly as before.
  zoomable?: boolean;
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

export function TrendChart({ points, specification, unit, controlLimits, zoomable = false }: TrendChartProps) {
  const data = points.map((p) => ({ ...p, label: formatDate(p.measuredAt) }));
  const upperLimit = specification.upperTol !== null ? specification.upperTol : undefined;
  const lowerLimit = specification.lowerTol !== null ? specification.lowerTol : undefined;

  // Zoom state is index-based (positions within `data`), not label-based --
  // formatted date labels can repeat for same-day points, so they're not a
  // reliable handle. `zoomRange` is always relative to the full `data`
  // array, so re-dragging on an already-zoomed chart narrows further, and
  // "Zoom Out" resets the whole way in one click.
  const [refAreaStart, setRefAreaStart] = useState<number | null>(null);
  const [refAreaEnd, setRefAreaEnd] = useState<number | null>(null);
  const [zoomRange, setZoomRange] = useState<{ start: number; end: number } | null>(null);

  const baseOffset = zoomRange ? zoomRange.start : 0;
  const visibleData = zoomRange ? data.slice(zoomRange.start, zoomRange.end + 1) : data;
  const dragging = zoomable && refAreaStart !== null && refAreaEnd !== null;

  function handleMouseDown(state: CategoricalChartState) {
    if (!zoomable || state.activeTooltipIndex == null) return;
    setRefAreaStart(state.activeTooltipIndex);
    setRefAreaEnd(state.activeTooltipIndex);
  }

  function handleMouseMove(state: CategoricalChartState) {
    if (!zoomable || refAreaStart === null || state.activeTooltipIndex == null) return;
    setRefAreaEnd(state.activeTooltipIndex);
  }

  function commitZoom() {
    if (refAreaStart !== null && refAreaEnd !== null && refAreaStart !== refAreaEnd) {
      const localStart = Math.min(refAreaStart, refAreaEnd);
      const localEnd = Math.max(refAreaStart, refAreaEnd);
      setZoomRange({ start: baseOffset + localStart, end: baseOffset + localEnd });
    }
    setRefAreaStart(null);
    setRefAreaEnd(null);
  }

  return (
    <div>
      {zoomable && zoomRange !== null && (
        <div className="mb-2 flex justify-end">
          <button
            type="button"
            onClick={() => setZoomRange(null)}
            className="inline-flex items-center gap-1.5 rounded border border-border px-2 py-1 text-xs font-medium text-text-secondary hover:border-brand-primary hover:text-text-primary"
          >
            <ZoomOut size={14} strokeWidth={2} aria-hidden="true" />
            Zoom out
          </button>
        </div>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <LineChart
          data={visibleData}
          margin={{ top: 8, right: 48, bottom: 0, left: 0 }}
          onMouseDown={zoomable ? handleMouseDown : undefined}
          onMouseMove={zoomable ? handleMouseMove : undefined}
          onMouseUp={zoomable ? commitZoom : undefined}
          onMouseLeave={zoomable ? commitZoom : undefined}
          style={zoomable ? { cursor: "crosshair" } : undefined}
        >
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
          {controlLimits && (
            <>
              <ReferenceLine
                y={controlLimits.centerLine}
                stroke="var(--chart-2)"
                strokeDasharray="6 3"
                label={{ value: "CL", position: "left", fontSize: 11, fill: "var(--chart-2)" }}
              />
              <ReferenceLine
                y={controlLimits.ucl}
                stroke="var(--chart-2)"
                strokeDasharray="1 3"
                label={{ value: "UCL", position: "left", fontSize: 11, fill: "var(--chart-2)" }}
              />
              <ReferenceLine
                y={controlLimits.lcl}
                stroke="var(--chart-2)"
                strokeDasharray="1 3"
                label={{ value: "LCL", position: "left", fontSize: 11, fill: "var(--chart-2)" }}
              />
            </>
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
          {dragging && refAreaStart !== null && refAreaEnd !== null && (
            <ReferenceArea
              x1={visibleData[Math.min(refAreaStart, refAreaEnd)]?.label}
              x2={visibleData[Math.max(refAreaStart, refAreaEnd)]?.label}
              strokeOpacity={0.3}
              fill="var(--brand-primary)"
              fillOpacity={0.1}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-1 text-xs text-text-secondary">
        Individual measurements (I-MR). Triangles mark NOK results; dashed red lines are the tolerance limits, dashed
        gray is nominal
        {controlLimits && (
          <>
            , dotted lines are the SPC control limits (UCL/LCL) around the{" "}
            <span className="inline-flex items-center gap-0.5 align-middle">
              CL
              <InfoTooltip label="What is CL?">
                CL — center line: the process average calculated by the SPC engine from the measurement history, used
                to set UCL/LCL. Not a tolerance limit.
              </InfoTooltip>
            </span>
          </>
        )}
        .
      </p>
    </div>
  );
}
