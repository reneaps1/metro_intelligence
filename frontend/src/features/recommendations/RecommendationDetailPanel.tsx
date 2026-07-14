import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { formatDateTime } from "../../lib/format";
import { getRecommendation, recordActionTaken } from "../../lib/recommendations/api";
import type { ActionOutcomeStatus, RecommendationDetail } from "../../lib/recommendations/types";
import { errorMessage } from "./DecisionModal";

const OUTCOME_LABELS: Record<ActionOutcomeStatus, string> = {
  pending: "Pending",
  effective: "Effective",
  ineffective: "Ineffective",
  not_applicable: "Not applicable",
};

// F5.9 (MI-38): evidence + decision history for one recommendation, fetched
// on expand (GET /recommendations/{id} carries the risk_assessment + decision
// nesting the list endpoint doesn't return).
export function RecommendationDetailPanel({
  recommendationId,
  canRecordOutcome,
}: {
  recommendationId: string;
  canRecordOutcome: boolean;
}) {
  const [detail, setDetail] = useState<RecommendationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recordingOutcome, setRecordingOutcome] = useState(false);
  const [outcomeDescription, setOutcomeDescription] = useState("");
  const [outcomeStatus, setOutcomeStatus] = useState<ActionOutcomeStatus>("effective");
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    getRecommendation(recommendationId)
      .then(setDetail)
      .catch((err: unknown) => setError(errorMessage(err)));
  };

  useEffect(load, [recommendationId]);

  if (error) return <p className="text-sm text-status-nok">{error}</p>;
  if (!detail) return <p className="text-sm text-text-secondary">Loading evidence…</p>;

  const { risk_assessment: risk, decision } = detail;

  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="font-medium text-text-primary">Evidence</p>
        <p className="mt-1 text-text-secondary">{detail.rationale}</p>
        <p className="mt-1 text-xs text-text-disabled">
          {detail.engine_name} · {detail.engine_version}
        </p>
        <Link
          to={`/measurements/${detail.characteristic_id}`}
          className="mt-1 inline-block text-xs text-brand-primary hover:underline"
        >
          View characteristic trend →
        </Link>
      </div>

      {risk && (
        <div>
          <p className="font-medium text-text-primary">
            Risk score {risk.score} · {risk.level}
          </p>
          <ul className="mt-1 list-inside list-disc text-text-secondary">
            {Object.entries(risk.factors).map(([key, value]) => (
              <li key={key}>
                {key}: {String(value)}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-text-disabled">
            {risk.engine_name} · {risk.engine_version} · {formatDateTime(risk.computed_at)}
          </p>
        </div>
      )}

      {decision && (
        <div className="rounded border border-border p-3">
          <p className="font-medium text-text-primary">
            {decision.action === "accepted" ? "Accepted" : "Rejected"} on {formatDateTime(decision.decided_at)}
          </p>
          {decision.comment && <p className="mt-1 text-text-secondary">"{decision.comment}"</p>}

          <p className="mt-3 text-xs font-medium text-text-secondary">Actions taken</p>
          {decision.actions_taken.length === 0 ? (
            <p className="text-xs text-text-disabled">No outcomes recorded yet.</p>
          ) : (
            <ul className="mt-1 space-y-1">
              {decision.actions_taken.map((action) => (
                <li key={action.id} className="text-xs text-text-secondary">
                  {action.description} — {OUTCOME_LABELS[action.outcome_status]} ({formatDateTime(action.created_at)}
                  )
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
                    disabled={outcomeDescription.trim().length === 0 || submitting}
                    loading={submitting}
                    onClick={() => {
                      setSubmitting(true);
                      recordActionTaken(decision.id, {
                        description: outcomeDescription.trim(),
                        outcome_status: outcomeStatus,
                      })
                        .then(() => {
                          setRecordingOutcome(false);
                          setOutcomeDescription("");
                          load();
                        })
                        .catch((err: unknown) => setError(errorMessage(err)))
                        .finally(() => setSubmitting(false));
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
