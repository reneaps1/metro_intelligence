import { useState } from "react";
import { Link } from "react-router-dom";
import { useDemoData } from "../../lib/mock/DataProvider";
import { useAuth } from "../../lib/auth/AuthProvider";
import { Card, CardHeader } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { StatusChip, riskLevelToChipStatus } from "../../components/ui/StatusChip";
import { RiskHeatmap } from "../../components/charts/RiskHeatmap";
import { formatDateTime } from "../../lib/format";
import type { RecommendationState } from "../../lib/mock/types";

const RECOMMENDATION_LABELS: Record<string, string> = {
  frequency_increase: "Increase inspection frequency",
  frequency_decrease: "Decrease inspection frequency",
  immediate_inspection: "Immediate inspection",
  investigate_cause: "Investigate cause",
  post_event_validation: "Post-event validation",
};

const STATE_CHIP: Record<RecommendationState, { status: "ok" | "nok" | "info" | "warning" | "neutral"; label: string }> = {
  pending: { status: "warning", label: "Pending" },
  accepted: { status: "ok", label: "Accepted" },
  rejected: { status: "nok", label: "Rejected" },
  superseded: { status: "neutral", label: "Superseded" },
  expired: { status: "neutral", label: "Expired" },
};

export function RiskPage() {
  const { characteristics, parts, riskAssessments, recommendations, getSeries, decideRecommendation } = useDemoData();
  const { user } = useAuth();
  const [commentDraft, setCommentDraft] = useState<Record<string, string>>({});
  const canDecide = user?.role === "quality_engineer" || user?.role === "admin";

  const heatmapRows = characteristics.map((characteristic) => ({
    characteristic,
    points: getSeries(characteristic.id),
  }));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Risk &amp; Recommendations</h1>
        <p className="text-sm text-text-secondary">Composite risk per characteristic and pending inspection-strategy recommendations.</p>
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
        <CardHeader title="Recommendations inbox" />
        <div className="space-y-3">
          {recommendations.map((rec) => {
            const characteristic = characteristics.find((c) => c.id === rec.characteristicId)!;
            const part = parts.find((p) => p.id === characteristic.partId);
            const chip = STATE_CHIP[rec.state];
            return (
              <div key={rec.id} className="rounded border border-border p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-xs text-text-secondary">
                      {part?.code} · {characteristic.name} · risk {rec.riskScore}
                    </p>
                    <p className="font-medium text-text-primary">{RECOMMENDATION_LABELS[rec.type]}</p>
                  </div>
                  <StatusChip status={chip.status} label={chip.label} />
                </div>
                <p className="mt-2 text-sm text-text-secondary">{rec.rationale}</p>
                <p className="mt-1 text-xs text-text-disabled">
                  {rec.ruleVersion} · created {formatDateTime(rec.createdAt)}
                </p>

                {rec.state !== "pending" ? (
                  <p className="mt-2 text-xs text-text-secondary">
                    {chip.label} by {rec.decidedBy} on {rec.decidedAt && formatDateTime(rec.decidedAt)} — “{rec.decisionComment}”
                  </p>
                ) : canDecide ? (
                  <div className="mt-3 space-y-2">
                    <label className="block text-xs font-medium text-text-secondary" htmlFor={`comment-${rec.id}`}>
                      Decision comment
                    </label>
                    <input
                      id={`comment-${rec.id}`}
                      type="text"
                      className="w-full rounded border border-border bg-surface px-3 py-2 text-sm text-text-primary"
                      placeholder="Why are you accepting or rejecting this?"
                      value={commentDraft[rec.id] ?? ""}
                      onChange={(e) => setCommentDraft((prev) => ({ ...prev, [rec.id]: e.target.value }))}
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="primary"
                        onClick={() =>
                          decideRecommendation(rec.id, "accepted", user!.email, commentDraft[rec.id] || "Accepted.")
                        }
                      >
                        Accept
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() =>
                          decideRecommendation(rec.id, "rejected", user!.email, commentDraft[rec.id] || "Rejected.")
                        }
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-text-disabled">
                    Only Quality Engineer or Admin roles can accept/reject recommendations.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
