import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { formatDateTime } from "../../lib/format";
import { useDemoData } from "../../lib/mock/DataProvider";
import type { ActionOutcomeStatus, Recommendation } from "../../lib/mock/types";

const OUTCOME_LABELS: Record<ActionOutcomeStatus, string> = {
  pending: "Pending",
  effective: "Effective",
  ineffective: "Ineffective",
  not_applicable: "Not applicable",
};

// F5.9 (MI-38): evidence + decision history for one recommendation. Reads
// straight off the shared demo catalog (useDemoData) so the characteristic id
// it links to always resolves on the Measurements/Trend page — recommendation,
// characteristic, and risk data all come from the same mock fixtures.
export function RecommendationDetailPanel({
  recommendation,
  canRecordOutcome,
}: {
  recommendation: Recommendation;
  canRecordOutcome: boolean;
}) {
  const { characteristics, riskAssessments, addActionTaken } = useDemoData();
  const [recordingOutcome, setRecordingOutcome] = useState(false);
  const [outcomeDescription, setOutcomeDescription] = useState("");
  const [outcomeStatus, setOutcomeStatus] = useState<ActionOutcomeStatus>("effective");

  const risk = riskAssessments.find((r) => r.characteristicId === recommendation.characteristicId) ?? null;
  const characteristicExists = characteristics.some((c) => c.id === recommendation.characteristicId);

  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="font-medium text-text-primary">Evidence</p>
        <p className="mt-1 text-text-secondary">{recommendation.rationale}</p>
        <p className="mt-1 text-xs text-text-disabled">{recommendation.ruleVersion}</p>
        {characteristicExists && (
          <Link
            to={`/measurements/${recommendation.characteristicId}`}
            className="mt-1 inline-block text-xs text-brand-primary hover:underline"
          >
            View characteristic trend →
          </Link>
        )}
      </div>

      {risk && (
        <div>
          <p className="font-medium text-text-primary">
            Risk score {risk.score} · {risk.level}
          </p>
          <ul className="mt-1 list-inside list-disc text-text-secondary">
            {risk.factors.map((factor) => (
              <li key={factor.label}>
                {factor.label}: {factor.contribution}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-text-disabled">
            {risk.engineVersion} · {formatDateTime(risk.computedAt)}
          </p>
        </div>
      )}

      {recommendation.decidedBy && (
        <div className="rounded border border-border p-3">
          <p className="font-medium text-text-primary">
            {recommendation.state === "accepted" ? "Accepted" : "Rejected"} on{" "}
            {formatDateTime(recommendation.decidedAt!)}
          </p>
          {recommendation.decisionComment && (
            <p className="mt-1 text-text-secondary">"{recommendation.decisionComment}"</p>
          )}

          <p className="mt-3 text-xs font-medium text-text-secondary">Actions taken</p>
          {recommendation.actionsTaken.length === 0 ? (
            <p className="text-xs text-text-disabled">No outcomes recorded yet.</p>
          ) : (
            <ul className="mt-1 space-y-1">
              {recommendation.actionsTaken.map((action) => (
                <li key={action.id} className="text-xs text-text-secondary">
                  {action.description} — {OUTCOME_LABELS[action.outcomeStatus]} ({formatDateTime(action.createdAt)})
                </li>
              ))}
            </ul>
          )}

          {canRecordOutcome &&
            (recordingOutcome ? (
              <div className="mt-2 space-y-2">
                <textarea
                  aria-label="Outcome description"
                  rows={2}
                  className="w-full rounded border border-border bg-surface px-3 py-2 text-xs text-text-primary"
                  placeholder="What happened after this decision?"
                  value={outcomeDescription}
                  onChange={(e) => setOutcomeDescription(e.target.value)}
                />
                <select
                  aria-label="Outcome status"
                  className="rounded border border-border bg-surface px-2 py-1 text-xs text-text-primary"
                  value={outcomeStatus}
                  onChange={(e) => setOutcomeStatus(e.target.value as ActionOutcomeStatus)}
                >
                  {(Object.keys(OUTCOME_LABELS) as ActionOutcomeStatus[]).map((status) => (
                    <option key={status} value={status}>
                      {OUTCOME_LABELS[status]}
                    </option>
                  ))}
                </select>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setRecordingOutcome(false);
                      setOutcomeDescription("");
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    disabled={outcomeDescription.trim().length === 0}
                    onClick={() => {
                      addActionTaken(recommendation.id, {
                        description: outcomeDescription.trim(),
                        outcomeStatus,
                      });
                      setRecordingOutcome(false);
                      setOutcomeDescription("");
                    }}
                  >
                    Save outcome
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="ghost" className="mt-2" onClick={() => setRecordingOutcome(true)}>
                Record outcome
              </Button>
            ))}
        </div>
      )}
    </div>
  );
}
