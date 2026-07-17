import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useDemoData } from "../../lib/mock/DataProvider";
import { Card, CardHeader } from "../../components/ui/Card";
import { StatusChip, riskLevelToChipStatus } from "../../components/ui/StatusChip";
import { RiskHeatmap } from "../../components/charts/RiskHeatmap";

export function RiskPage() {
  // Risk scoring itself is still F5.M mock data -- the Risk Engine (F9) isn't
  // built yet. Recommendations (F5.9 / MI-38) are wired to the real F4.8 API
  // in their own screen at /recommendations, not duplicated here.
  const { characteristics, parts, riskAssessments, getSeries } = useDemoData();

  const heatmapRows = characteristics.map((characteristic) => ({
    characteristic,
    points: getSeries(characteristic.id),
  }));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Risk</h1>
        <p className="text-sm text-text-secondary">Composite risk per characteristic (proxy data).</p>
      </div>

      <Card>
        <CardHeader title="Risk overview (proxy, weekly)" />
        <RiskHeatmap rows={heatmapRows} />
      </Card>

      <Card className="overflow-x-auto p-0">
        <div className="p-4 pb-0">
          <CardHeader title="Risk by characteristic" />
        </div>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs text-text-secondary">
              <th className="p-3 font-medium">Part</th>
              <th className="p-3 font-medium">Characteristic</th>
              <th className="p-3 font-medium">Score</th>
              <th className="p-3 font-medium">Level</th>
              <th className="p-3 font-medium">Top factor</th>
            </tr>
          </thead>
          <tbody>
            {riskAssessments.map((risk) => {
              const characteristic = characteristics.find((c) => c.id === risk.characteristicId)!;
              const part = parts.find((p) => p.id === characteristic.partId);
              const topFactor = [...risk.factors].sort((a, b) => b.contribution - a.contribution)[0];
              return (
                <tr key={risk.characteristicId} className="border-b border-border last:border-0 hover:bg-surface-app">
                  <td className="p-3 font-mono text-xs">{part?.code}</td>
                  <td className="p-3">
                    <Link to={`/measurements/${characteristic.id}`} className="text-brand-primary hover:underline">
                      {characteristic.name}
                    </Link>
                  </td>
                  <td className="p-3 font-mono">{risk.score}</td>
                  <td className="p-3">
                    <StatusChip status={riskLevelToChipStatus(risk.level)} label={risk.level} />
                  </td>
                  <td className="p-3 text-xs text-text-secondary">{topFactor.label}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <Card>
        <CardHeader title="Recommendations" />
        <p className="mb-2 text-xs text-text-secondary">
          Live backend data — may not correspond 1:1 with the risk rows above (proxy/demo data).
        </p>
        <Link
          to="/recommendations"
          className="inline-flex items-center gap-1 text-sm font-medium text-brand-primary hover:underline"
        >
          Open the recommendations inbox <ArrowRight size={16} />
        </Link>
      </Card>
    </div>
  );
}
