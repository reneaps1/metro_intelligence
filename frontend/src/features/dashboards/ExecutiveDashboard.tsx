import { useDemoData } from "../../lib/mock/DataProvider";
import { cpkForCharacteristic, weeklyAggregateOkRate } from "../../lib/mock/analytics";
import { StatTile } from "../../components/ui/StatTile";
import { Card, CardHeader } from "../../components/ui/Card";

export function ExecutiveDashboard() {
  const { characteristics, getSeries, recommendations } = useDemoData();

  const allSeries = characteristics.map((c) => getSeries(c.id));
  const avgCpk =
    characteristics.reduce((sum, c) => sum + cpkForCharacteristic(c, getSeries(c.id)), 0) / characteristics.length;
  const okRateTrend = weeklyAggregateOkRate(allSeries);
  const overallOkRate = okRateTrend.at(-1) ?? 100;
  const frequencyDecreaseCandidates = recommendations.filter(
    (r) => r.type === "frequency_decrease" && r.state !== "rejected"
  ).length;
  const pendingCount = recommendations.filter((r) => r.state === "pending").length;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Average Cpk"
          value={avgCpk.toFixed(2)}
          delta={{ value: avgCpk >= 1.33 ? "Capable" : "Below target", direction: avgCpk >= 1.33 ? "up" : "down", positive: avgCpk >= 1.33 }}
        />
        <StatTile label="OK rate (last week)" value={`${overallOkRate}%`} sparklineValues={okRateTrend} />
        <StatTile
          label="Inspection savings opportunities"
          value={String(frequencyDecreaseCandidates)}
          delta={{ value: "characteristics", direction: "up", positive: true }}
        />
        <StatTile label="Pending recommendations" value={String(pendingCount)} />
      </div>

      <Card>
        <CardHeader title="Quality KPI trend (OK rate, last 6 weeks)" />
        <div className="flex items-end gap-4">
          {okRateTrend.map((rate, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <div
                className="w-8 rounded-t bg-brand-accent"
                style={{ height: `${Math.max(4, rate)}px` }}
                title={`Week ${i + 1}: ${rate}% OK`}
              />
              <span className="font-mono text-xs text-text-secondary">{rate}%</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
