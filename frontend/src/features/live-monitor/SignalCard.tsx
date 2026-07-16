import clsx from "clsx";
import { Card } from "../../components/ui/Card";
import { Sparkline } from "../../components/charts/Sparkline";
import { StatusChip } from "../../components/ui/StatusChip";
import type { ControlLimitsUpdatedEvent, PointEvent } from "../../lib/live-monitor/types";

// LM.1 (docs/tasks/LM1-live-monitor-mvp.md): one characteristic's live tile.
// Everything shown traces to a real engine output (`engine_name`/
// `engine_version` on the point/control-limits events) -- never a bare
// number without its source, per docs/design/live-monitor-panel.md's
// "honest framing" decision.
//
// LM.2 (docs/tasks/LM2-live-monitor-detail-view.md): `points` is the full
// replayed series (for the detail panel), not just a sparkline-sized slice --
// this component takes the last `SPARKLINE_POINTS` of it for its own preview
// so the caller doesn't have to hold two different arrays.
const SPARKLINE_POINTS = 30;

export function SignalCard({
  characteristicName,
  partCode,
  unit,
  points,
  controlLimits,
  onClick,
  selected = false,
}: {
  characteristicName: string;
  partCode: string;
  unit: string;
  points: PointEvent[];
  controlLimits: ControlLimitsUpdatedEvent | null;
  onClick?: () => void;
  selected?: boolean;
}) {
  const lastPoint = points[points.length - 1] ?? null;
  const values = points.slice(-SPARKLINE_POINTS).map((p) => Number(p.value));

  return (
    <Card
      className={clsx(
        "space-y-2",
        onClick && "cursor-pointer transition-colors hover:border-brand-primary",
        selected && "border-brand-primary ring-1 ring-brand-primary",
      )}
    >
      <button
        type="button"
        onClick={onClick}
        disabled={!onClick}
        className="w-full space-y-2 text-left disabled:cursor-default"
        aria-pressed={selected}
      >
        <div>
          <p className="truncate text-sm font-medium text-text-primary" title={characteristicName}>
            {characteristicName}
          </p>
          <p className="truncate text-xs text-text-secondary" title={partCode}>
            {partCode}
          </p>
        </div>

        <div className="flex h-8 items-center">
          {values.length >= 2 ? (
            <Sparkline values={values} width={140} height={32} />
          ) : (
            <span className="text-xs text-text-secondary">Waiting for data…</span>
          )}
        </div>

        <div className="flex items-center justify-between">
          <span className="font-mono text-sm text-text-primary">
            {lastPoint ? `${Number(lastPoint.value).toFixed(3)} ${unit}` : "--"}
          </span>
          {lastPoint && <StatusChip status={lastPoint.is_ok ? "ok" : "nok"} />}
        </div>

        {controlLimits && (
          <p className="text-xs text-text-secondary" title={lastPoint?.rationale}>
            Cpk {controlLimits.cpk ? Number(controlLimits.cpk).toFixed(2) : "n/a"} ({controlLimits.engine_name}{" "}
            {controlLimits.engine_version})
          </p>
        )}
      </button>
    </Card>
  );
}
