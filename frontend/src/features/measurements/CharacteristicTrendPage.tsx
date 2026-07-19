import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { getCharacteristic, getPartNumber, listClassifications } from "../../lib/catalog/api";
import type { PartNumber } from "../../lib/catalog/types";
import { formatSpecification } from "../../lib/catalog/format";
import { getCapabilityHistory, getCharacteristicSeries } from "../../lib/live-monitor/api";
import { useAsync } from "../../lib/catalog/hooks";
import { TrendChart } from "../../components/charts/TrendChart";
import { Histogram } from "../../components/charts/Histogram";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatTile } from "../../components/ui/StatTile";

// F5.7 follow-up: migrated off useDemoData() onto the real API -- this page
// used to look characteristicId up in the mock fixtures array, which never
// matches a real Postgres UUID, so any link into here from an
// already-migrated page (e.g. RecommendationDetailPanel's "View
// characteristic trend") always rendered "Characteristic not found.".
// Mirrors LiveMonitorDetailPage.tsx's real-API fetch pattern.
export function CharacteristicTrendPage() {
  const { characteristicId } = useParams<{ characteristicId: string }>();
  const id = characteristicId ?? "";

  const characteristic = useAsync(
    () => (id ? getCharacteristic(id) : Promise.reject(new Error("Missing characteristic id"))),
    [id],
  );
  const partNumberId = characteristic.data?.part_number_id ?? null;
  // Tolerant of failure (falls back to "--") -- a part lookup failing isn't
  // reason to hide the characteristic itself, same convention as
  // LiveMonitorDetailPage's `context?.part?.code ?? "--"`.
  const [part, setPart] = useState<PartNumber | null>(null);
  useEffect(() => {
    if (!partNumberId) return;
    let cancelled = false;
    getPartNumber(partNumberId)
      .then((p) => {
        if (!cancelled) setPart(p);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [partNumberId]);

  const classifications = useAsync(() => listClassifications(), []);
  const series = useAsync(
    () => (id ? getCharacteristicSeries(id, {}) : Promise.reject(new Error("Missing characteristic id"))),
    [id],
  );
  const capability = useAsync(
    () => (id ? getCapabilityHistory(id, { windowSize: 20 }) : Promise.reject(new Error("Missing characteristic id"))),
    [id],
  );

  if (!id) {
    return <p className="text-text-secondary">No characteristic specified.</p>;
  }
  if (characteristic.loading && !characteristic.data) {
    return <p className="text-text-secondary">Loading…</p>;
  }
  if (characteristic.error) {
    return <p className="text-text-secondary">{characteristic.error}</p>;
  }
  if (!characteristic.data) {
    return null;
  }

  const c = characteristic.data;
  const activeSpec = c.active_specification;
  const classificationName =
    classifications.data?.items.find((cl) => cl.id === c.classification_id)?.name ?? "—";

  const trendPoints = (series.data?.points ?? []).map((p, index) => ({
    measuredAt: p.measured_at,
    value: Number(p.value),
    deviation: Number(p.deviation),
    isOk: p.is_ok,
    sampleIndex: index,
  }));
  const trendSpecification = activeSpec
    ? {
        nominal: Number(activeSpec.nominal),
        lowerTol: activeSpec.lower_tol !== null ? Number(activeSpec.lower_tol) : null,
        upperTol: activeSpec.upper_tol !== null ? Number(activeSpec.upper_tol) : null,
        unit: activeSpec.unit,
      }
    : null;

  const windows = capability.data?.windows ?? [];
  const latestWindow = [...windows].reverse().find((w) => w.cpk !== null) ?? null;
  const cpkValue = latestWindow?.cpk !== null && latestWindow ? Number(latestWindow.cpk) : null;
  const nokCount = trendPoints.filter((p) => !p.isOk).length;

  return (
    <div className="space-y-4">
      <Link
        to={`/catalog/${c.part_number_id}`}
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
      >
        <ArrowLeft size={16} /> Back to {part?.name ?? "part"}
      </Link>
      <div>
        <p className="font-mono text-xs text-text-secondary">
          {part?.code ?? "—"} · Balloon #{c.balloon_number}
        </p>
        <h1 className="text-xl font-semibold text-text-primary">{c.name}</h1>
        <p className="text-sm text-text-secondary">
          {classificationName}
          {activeSpec && ` · ${formatSpecification(activeSpec)}`}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Cpk (most recent window)" value={cpkValue !== null ? cpkValue.toFixed(2) : "—"} />
        <StatTile label="NOK results" value={`${nokCount} / ${trendPoints.length}`} />
        <StatTile label="Samples" value={String(series.data?.total_points ?? 0)} />
        <StatTile label="Classification" value={classificationName} />
      </div>

      {series.error && <p className="text-sm text-status-nok">{series.error}</p>}
      {capability.error && <p className="text-sm text-status-nok">{capability.error}</p>}

      <Card>
        <CardHeader title="Trend (I-MR)" />
        {series.loading && !series.data ? (
          <p className="text-sm text-text-secondary">Loading trend…</p>
        ) : trendPoints.length >= 2 && trendSpecification ? (
          <TrendChart points={trendPoints} specification={trendSpecification} unit={trendSpecification.unit} />
        ) : (
          <p className="text-sm text-text-secondary">Not enough points in this range to plot a trend.</p>
        )}
      </Card>

      <Card>
        <CardHeader title="Capability — distribution" />
        {series.loading && !series.data ? (
          <p className="text-sm text-text-secondary">Loading…</p>
        ) : trendPoints.length > 0 && trendSpecification ? (
          <Histogram points={trendPoints} specification={trendSpecification} />
        ) : (
          <p className="text-sm text-text-secondary">Not enough points to plot a distribution.</p>
        )}
      </Card>
    </div>
  );
}
