import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useAuth } from "../../lib/auth/AuthProvider";
import { useAsync } from "../../lib/catalog/hooks";
import { useCharacteristicContexts } from "../../lib/recommendations/hooks";
import { decideRecommendation, listRecommendations } from "../../lib/recommendations/api";
import type {
  DecisionAction,
  Recommendation,
  RecommendationState,
  RecommendationType,
} from "../../lib/recommendations/types";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { StatusChip, type ChipStatus } from "../../components/ui/StatusChip";
import { formatDateTime } from "../../lib/format";
import { DecisionModal, errorMessage } from "./DecisionModal";
import { RecommendationDetailPanel } from "./RecommendationDetailPanel";

// F5.9 (MI-38): CLAUDE.md §24 -- state must always be visible and never
// implied as "in force" before a human decision. Every row shows this chip.
const STATE_CHIP: Record<RecommendationState, { status: ChipStatus; label: string }> = {
  pending: { status: "warning", label: "Pending" },
  accepted: { status: "ok", label: "Accepted" },
  rejected: { status: "nok", label: "Rejected" },
  superseded: { status: "neutral", label: "Superseded" },
  expired: { status: "neutral", label: "Expired" },
};

const TYPE_LABELS: Record<RecommendationType, string> = {
  frequency_increase: "Increase inspection frequency",
  frequency_decrease: "Decrease inspection frequency",
  immediate_inspection: "Immediate inspection",
  investigate_cause: "Investigate cause",
  post_event_validation: "Post-event validation",
};

export function RecommendationsInboxPage() {
  const { user } = useAuth();
  const canDecide = user?.role === "quality_engineer" || user?.role === "admin";

  const [stateFilter, setStateFilter] = useState<RecommendationState | "">("");
  const [typeFilter, setTypeFilter] = useState<RecommendationType | "">("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<{ id: string; action: DecisionAction } | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);
  const [deciding, setDeciding] = useState(false);

  const list = useAsync(() => listRecommendations({ state: stateFilter || undefined }), [stateFilter]);
  const items = list.data?.items ?? [];
  const contexts = useCharacteristicContexts(items.map((item) => item.characteristic_id));

  const visibleItems = useMemo(
    () => (typeFilter ? items.filter((item) => item.recommendation_type === typeFilter) : items),
    [items, typeFilter],
  );

  function confirmDecision(comment: string) {
    if (!pendingDecision) return;
    setDeciding(true);
    setDecisionError(null);
    decideRecommendation(pendingDecision.id, pendingDecision.action, comment)
      .then(() => {
        setPendingDecision(null);
        list.refetch();
      })
      .catch((err: unknown) => setDecisionError(errorMessage(err)))
      .finally(() => setDeciding(false));
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Recommendations</h1>
        <p className="text-sm text-text-secondary">
          Inspection-strategy recommendations awaiting review — every decision is traceable (CLAUDE.md §24).
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <select
          aria-label="Filter by state"
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value as RecommendationState | "")}
          className="min-h-[44px] rounded border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info"
        >
          <option value="">All states</option>
          {(Object.keys(STATE_CHIP) as RecommendationState[]).map((state) => (
            <option key={state} value={state}>
              {STATE_CHIP[state].label}
            </option>
          ))}
        </select>
        <select
          aria-label="Filter by recommendation type"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as RecommendationType | "")}
          className="min-h-[44px] rounded border border-border bg-surface px-3 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info"
        >
          <option value="">All types</option>
          {(Object.keys(TYPE_LABELS) as RecommendationType[]).map((type) => (
            <option key={type} value={type}>
              {TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>

      {list.loading && list.data === null && <p className="text-sm text-text-secondary">Loading recommendations…</p>}
      {list.error && <p className="text-sm text-status-nok">{list.error}</p>}
      {list.data !== null && !list.error && visibleItems.length === 0 && (
        <p className="text-sm text-text-secondary">No recommendations match these filters.</p>
      )}

      <div className="space-y-3">
        {visibleItems.map((rec: Recommendation) => {
          const context = contexts[rec.characteristic_id];
          const chip = STATE_CHIP[rec.state];
          const expanded = expandedId === rec.id;
          return (
            <Card key={rec.id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-xs text-text-secondary">
                    {context ? `${context.part?.code ?? "—"} · ${context.characteristic.name}` : "Loading…"}
                  </p>
                  <p className="font-medium text-text-primary">{TYPE_LABELS[rec.recommendation_type]}</p>
                </div>
                <StatusChip status={chip.status} label={chip.label} />
              </div>
              <p className="mt-2 text-sm text-text-secondary">{rec.rationale}</p>
              <p className="mt-1 text-xs text-text-disabled">
                {rec.engine_name} {rec.engine_version} · created {formatDateTime(rec.created_at)}
              </p>

              <div className="mt-3 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => setExpandedId(expanded ? null : rec.id)}
                  className="inline-flex min-h-[44px] items-center gap-1 text-sm font-medium text-brand-primary hover:underline"
                >
                  {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  {expanded ? "Hide evidence" : "View evidence & history"}
                </button>

                {rec.state === "pending" &&
                  (canDecide ? (
                    <div className="flex gap-2">
                      <Button
                        variant="primary"
                        onClick={() => {
                          setDecisionError(null);
                          setPendingDecision({ id: rec.id, action: "accepted" });
                        }}
                      >
                        Accept
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() => {
                          setDecisionError(null);
                          setPendingDecision({ id: rec.id, action: "rejected" });
                        }}
                      >
                        Reject
                      </Button>
                    </div>
                  ) : (
                    <p className="text-xs text-text-disabled">
                      Only Quality Engineer or Admin roles can accept/reject recommendations.
                    </p>
                  ))}
              </div>

              {expanded && (
                <div className="mt-3 border-t border-border pt-3">
                  <RecommendationDetailPanel recommendationId={rec.id} canRecordOutcome={canDecide} />
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {pendingDecision && (
        <DecisionModal
          action={pendingDecision.action}
          submitting={deciding}
          error={decisionError}
          onConfirm={confirmDecision}
          onCancel={() => {
            setPendingDecision(null);
            setDecisionError(null);
          }}
        />
      )}
    </div>
  );
}
