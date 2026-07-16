import { Link } from "react-router-dom";
import { TrendChart } from "../../components/charts/TrendChart";
import type { Specification } from "../../lib/catalog/types";
import type { ControlLimitsUpdatedEvent, PointEvent } from "../../lib/live-monitor/types";

// LM.2 (docs/tasks/LM2-live-monitor-detail-view.md): the explainable-evidence
// panel opened from a `SignalCard` click. Same pattern as
// `RecommendationDetailPanel` (F5.9): rationale text + engine attribution,
// no bare numbers.
//
// Cpk >= 1.33 is the standard SPC convention for "capable" -- used here only
// to phrase the real Cpk value from the WS event in words, never to
// recompute or approximate it (CLAUDE.md §16, §22).
const CPK_CAPABLE_THRESHOLD = 1.33;

function capabilityRationale(controlLimits: ControlLimitsUpdatedEvent): string {
  if (controlLimits.cpk === null) {
    return "Cpk is undefined for this window (zero variance so far, or a unilateral characteristic) -- the control limits below are still real, computed values.";
  }
  const cpk = Number(controlLimits.cpk);
  const verdict =
    cpk >= CPK_CAPABLE_THRESHOLD
      ? `at or above the ${CPK_CAPABLE_THRESHOLD} capability threshold`
      : `below the ${CPK_CAPABLE_THRESHOLD} capability threshold`;
  return `Cpk ${cpk.toFixed(2)} -- ${verdict}.`;
}

export function SignalDetailPanel({
  characteristicId,
  unit,
  specification,
  points,
  controlLimits,
}: {
  characteristicId: string;
  unit: string;
  specification: Specification | null;
  points: PointEvent[];
  controlLimits: ControlLimitsUpdatedEvent | null;
}) {
  const lastPoint = points[points.length - 1] ?? null;

  // LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md) hasn't been built yet --
  // per LM.2's own spec, fall back to the existing (mock-data) measurements
  // trend page rather than link to a route that doesn't exist. Flip this to
  // `/live-monitor/${characteristicId}` once LM.4 lands.
  const fullDetailHref = `/measurements/${characteristicId}`;

  if (!specification) {
    return <p className="text-sm text-text-secondary">Loading specification…</p>;
  }

  const nominal = Number(specification.nominal);
  const trendSpecification = {
    nominal,
    lowerTol: specification.lower_tol !== null ? Number(specification.lower_tol) : null,
    upperTol: specification.upper_tol !== null ? Number(specification.upper_tol) : null,
    unit,
  };

  const trendPoints = points.map((point, index) => ({
    measuredAt: point.measured_at,
    value: Number(point.value),
    deviation: Number(point.deviation),
    isOk: point.is_ok,
    sampleIndex: index,
  }));

  // Control limits come back from the engine in raw-value space (same space
  // as `cpk()`/`individuals_moving_range_limits()` operate in); TrendChart
  // plots deviation, so they're shifted by nominal the same way tolerance
  // limits already are -- never recomputed, just re-expressed.
  const trendControlLimits = controlLimits
    ? {
        centerLine: Number(controlLimits.center_line) - nominal,
        ucl: Number(controlLimits.ucl) - nominal,
        lcl: Number(controlLimits.lcl) - nominal,
      }
    : null;

  return (
    <div className="space-y-3 text-sm">
      {trendPoints.length >= 2 ? (
        <TrendChart
          points={trendPoints}
          specification={trendSpecification}
          unit={unit}
          controlLimits={trendControlLimits}
        />
      ) : (
        <p className="text-text-secondary">Waiting for enough replayed points to plot a trend…</p>
      )}

      {lastPoint && (
        <div>
          <p className="font-medium text-text-primary">Compliance</p>
          <p className="mt-1 text-text-secondary">{lastPoint.rationale}</p>
          <p className="mt-1 text-xs text-text-disabled">
            {lastPoint.engine_name} · {lastPoint.engine_version}
          </p>
        </div>
      )}

      {controlLimits && (
        <div>
          <p className="font-medium text-text-primary">Process capability</p>
          <p className="mt-1 text-text-secondary">{capabilityRationale(controlLimits)}</p>
          <p className="mt-1 text-xs text-text-disabled">
            {controlLimits.engine_name} · {controlLimits.engine_version}
          </p>
        </div>
      )}

      <Link to={fullDetailHref} className="inline-block text-xs text-brand-primary hover:underline">
        View full detail →
      </Link>
    </div>
  );
}
