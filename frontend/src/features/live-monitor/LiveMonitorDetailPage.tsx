import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useCharacteristicContexts } from "../../lib/recommendations/hooks";
import { getCapabilityHistory, getCharacteristicSeries } from "../../lib/live-monitor/api";
import type { CapabilityWindow } from "../../lib/live-monitor/types";
import { useAsync } from "../../lib/catalog/hooks";
import { formatSpecification } from "../../lib/catalog/format";
import { TrendChart } from "../../components/charts/TrendChart";
import { CapabilityHistoryChart } from "../../components/charts/CapabilityHistoryChart";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatTile } from "../../components/ui/StatTile";

// LM.4 code-review fix: `window` can belong to an older specification
// version than the characteristic's *current* one (a window closes early at
// a spec-version boundary, so a short trailing window under a newer spec can
// have cpk=null and get skipped when picking "the latest window with a
// defined Cpk", falling back to a window still under an older spec).
// Converting its absolute center_line/ucl/lcl to deviation-space MUST use
// that window's own `nominal` -- never the characteristic's current active
// spec's nominal -- or the converted values are silently offset by the
// nominal delta between spec versions. Exported as its own pure function so
// this specific conversion is unit-testable without rendering the chart.
export function computeTrendControlLimits(
  window: CapabilityWindow | null,
): { centerLine: number; ucl: number; lcl: number } | null {
  if (!window || window.nominal === null) return null;
  if (window.center_line === null || window.ucl === null || window.lcl === null) return null;
  const nominal = Number(window.nominal);
  return {
    centerLine: Number(window.center_line) - nominal,
    ucl: Number(window.ucl) - nominal,
    lcl: Number(window.lcl) - nominal,
  };
}

// LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md): points are windowed by
// count (not time) in the capability-history request -- 20 mirrors F10.D's
// own minimum-history threshold for trusting a stability signal, a
// reasonable "enough points to mean something" default for this page too.
const CAPABILITY_WINDOW_SIZE = 20;
const DAY_MS = 24 * 60 * 60 * 1000;

type RangePreset = "7d" | "30d" | "90d" | "all";

const RANGE_OPTIONS: { value: RangePreset; label: string; days: number | null }[] = [
  { value: "7d", label: "7d", days: 7 },
  { value: "30d", label: "30d", days: 30 },
  { value: "90d", label: "90d", days: 90 },
  { value: "all", label: "All", days: null },
];

export function LiveMonitorDetailPage() {
  const { characteristicId } = useParams<{ characteristicId: string }>();
  const id = characteristicId ?? "";
  const contexts = useCharacteristicContexts(id ? [id] : []);
  const context = contexts[id];

  const [range, setRange] = useState<RangePreset>("all");
  // Anchored to the characteristic's own last real measurement, never to
  // wall-clock "now" -- the seed's history is generated relative to when it
  // was run, not to whenever someone happens to open this page (a "last 7
  // days" computed from real time would show nothing on a demo seeded weeks
  // ago). Captured once, from the first ("all") load.
  const [latestMeasuredAt, setLatestMeasuredAt] = useState<string | null>(null);

  const computedRange = useMemo(() => {
    const preset = RANGE_OPTIONS.find((o) => o.value === range);
    if (!preset?.days || !latestMeasuredAt) return {};
    const to = new Date(latestMeasuredAt);
    const from = new Date(to.getTime() - preset.days * DAY_MS);
    return { from: from.toISOString(), to: to.toISOString() };
  }, [range, latestMeasuredAt]);

  const series = useAsync(
    () => (id ? getCharacteristicSeries(id, computedRange) : Promise.reject(new Error("Missing characteristic id"))),
    [id, computedRange.from, computedRange.to],
  );
  const capability = useAsync(
    () =>
      id
        ? getCapabilityHistory(id, { ...computedRange, windowSize: CAPABILITY_WINDOW_SIZE })
        : Promise.reject(new Error("Missing characteristic id")),
    [id, computedRange.from, computedRange.to],
  );

  useEffect(() => {
    if (latestMeasuredAt === null && series.data && series.data.points.length > 0) {
      setLatestMeasuredAt(series.data.points[series.data.points.length - 1].measured_at);
    }
  }, [series.data, latestMeasuredAt]);

  const activeSpec = context?.characteristic.active_specification ?? null;
  const nominal = activeSpec ? Number(activeSpec.nominal) : 0;

  const trendPoints = (series.data?.points ?? []).map((p, index) => ({
    measuredAt: p.measured_at,
    value: Number(p.value),
    deviation: Number(p.deviation),
    isOk: p.is_ok,
    sampleIndex: index,
  }));

  const trendSpecification = activeSpec
    ? {
        nominal,
        lowerTol: activeSpec.lower_tol !== null ? Number(activeSpec.lower_tol) : null,
        upperTol: activeSpec.upper_tol !== null ? Number(activeSpec.upper_tol) : null,
        unit: activeSpec.unit,
      }
    : null;

  const windows = capability.data?.windows ?? [];
  const latestWindow = [...windows].reverse().find((w) => w.cpk !== null) ?? null;
  const trendControlLimits = computeTrendControlLimits(latestWindow);

  const isRefetching = (series.loading && series.data !== null) || (capability.loading && capability.data !== null);
  const isFirstLoad = series.loading && series.data === null;

  if (!id) {
    return <p className="text-text-secondary">No characteristic specified.</p>;
  }

  return (
    <div className="space-y-4">
      <Link
        to="/live-monitor"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
      >
        <ArrowLeft size={16} /> Back to Live Monitor
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-text-secondary">
            {context?.part?.code ?? "—"}
            {context && ` · Balloon #${context.characteristic.balloon_number}`}
          </p>
          <h1 className="text-xl font-semibold text-text-primary">{context?.characteristic.name ?? "Loading…"}</h1>
          {activeSpec && <p className="text-sm text-text-secondary">{formatSpecification(activeSpec)}</p>}
        </div>

        <div className="flex gap-1 rounded border border-border bg-surface p-1" role="group" aria-label="Date range">
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setRange(option.value)}
              disabled={option.days !== null && latestMeasuredAt === null}
              aria-pressed={range === option.value}
              className={`min-h-[36px] min-w-[44px] rounded px-3 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                range === option.value
                  ? "bg-brand-primary text-text-on-brand"
                  : "text-text-secondary hover:bg-surface-app"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile
          label="Cpk (most recent window)"
          value={latestWindow?.cpk !== null && latestWindow ? Number(latestWindow.cpk).toFixed(2) : "—"}
        />
        <StatTile label="Points in range" value={String(series.data?.total_points ?? 0)} />
        <StatTile label="Windows" value={String(windows.length)} />
        <StatTile
          label="Engine"
          value={latestWindow?.engine_name ? `${latestWindow.engine_name} ${latestWindow.engine_version}` : "—"}
        />
      </div>

      {series.error && <p className="text-sm text-status-nok">{series.error}</p>}
      {capability.error && <p className="text-sm text-status-nok">{capability.error}</p>}

      <Card className={isRefetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
        <CardHeader title="Trend (I-MR) — tolerance and control limits" />
        {isFirstLoad ? (
          <p className="text-sm text-text-secondary">Loading trend…</p>
        ) : trendPoints.length >= 2 && trendSpecification ? (
          <TrendChart
            points={trendPoints}
            specification={trendSpecification}
            unit={trendSpecification.unit}
            controlLimits={trendControlLimits}
          />
        ) : (
          <p className="text-sm text-text-secondary">Not enough points in this range to plot a trend.</p>
        )}
      </Card>

      <Card className={isRefetching ? "opacity-60 transition-opacity" : "transition-opacity"}>
        <CardHeader title="Cpk history" />
        {isFirstLoad ? (
          <p className="text-sm text-text-secondary">Loading capability history…</p>
        ) : windows.length > 0 ? (
          <>
            <CapabilityHistoryChart windows={windows} />
            <p className="mt-2 text-xs text-text-secondary">
              Each bar is one real, independently computed window of {CAPABILITY_WINDOW_SIZE} measurements (fewer at
              a specification-version boundary) — dashed line marks the standard 1.33 capability threshold.
            </p>
          </>
        ) : (
          <p className="text-sm text-text-secondary">Not enough points in this range to compute capability history.</p>
        )}
      </Card>
    </div>
  );
}
