import clsx from "clsx";
import { Card } from "../../components/ui/Card";
import { Sparkline } from "../../components/charts/Sparkline";
import { StatusChip, type ChipStatus } from "../../components/ui/StatusChip";
import type { AlertCreatedEvent, ControlLimitsUpdatedEvent, PointEvent } from "../../lib/live-monitor/types";

// Live Monitor alarm fix (2026-07): real, persisted alarms
// (app.services.alarm_detection_service), not a client-side heuristic --
// this only picks which *one* of possibly several open alerts to headline
// on the compact card (severity order, most recent as tiebreaker); the full
// list lives on the deep-dive page (LiveMonitorDetailPage).
const SEVERITY_RANK: Record<AlertCreatedEvent["severity"], number> = { critical: 3, warning: 2, info: 1 };

function mostSevereAlert(alerts: AlertCreatedEvent[]): AlertCreatedEvent | null {
  if (alerts.length === 0) return null;
  return [...alerts].sort(
    (a, b) =>
      SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity] ||
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )[0];
}

function alertChipStatus(severity: AlertCreatedEvent["severity"]): ChipStatus {
  if (severity === "critical") return "critical";
  if (severity === "warning") return "warning";
  return "info";
}

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
  openAlerts = [],
  onClick,
  selected = false,
}: {
  characteristicName: string;
  partCode: string;
  unit: string;
  points: PointEvent[];
  controlLimits: ControlLimitsUpdatedEvent | null;
  openAlerts?: AlertCreatedEvent[];
  onClick?: () => void;
  selected?: boolean;
}) {
  const lastPoint = points[points.length - 1] ?? null;
  const values = points.slice(-SPARKLINE_POINTS).map((p) => Number(p.value));
  const headlineAlert = mostSevereAlert(openAlerts);

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

        {headlineAlert && (
          // Native `title` (not `InfoTooltip`) on purpose -- this whole card
          // is already one `<button>` (onClick above), and `InfoTooltip`
          // renders its own nested `<button>`, which is invalid HTML inside
          // an interactive element. Full rationale + acknowledge action live
          // one click away on the deep-dive page (LiveMonitorDetailPage).
          <span title={headlineAlert.rationale}>
            <StatusChip
              status={alertChipStatus(headlineAlert.severity)}
              label={`Alarm${openAlerts.length > 1 ? ` (+${openAlerts.length - 1})` : ""}`}
            />
          </span>
        )}

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
