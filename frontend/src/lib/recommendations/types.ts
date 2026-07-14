// F5.9 (MI-38): mirrors backend/app/schemas/intelligence.py (F4.8).
import type { Page } from "../catalog/types";

export type { Page };

export type RecommendationState = "pending" | "accepted" | "rejected" | "superseded" | "expired";
export type RecommendationType =
  | "frequency_increase"
  | "frequency_decrease"
  | "immediate_inspection"
  | "investigate_cause"
  | "post_event_validation";
export type DecisionAction = "accepted" | "rejected";
export type ActionOutcomeStatus = "pending" | "effective" | "ineffective" | "not_applicable";

export interface RiskAssessmentSnapshot {
  id: string;
  score: number;
  level: string;
  factors: Record<string, unknown>;
  engine_name: string;
  engine_version: string;
  computed_at: string;
}

export interface ActionTaken {
  id: string;
  description: string;
  outcome_status: ActionOutcomeStatus;
  observed_at: string | null;
  created_at: string;
}

export interface Decision {
  id: string;
  recommendation_id: string;
  decided_by_user_id: string;
  action: DecisionAction;
  comment: string | null;
  decided_at: string;
  actions_taken: ActionTaken[];
}

export interface Recommendation {
  id: string;
  characteristic_id: string;
  recommendation_type: RecommendationType;
  rationale: string;
  evidence: Record<string, unknown>;
  engine_name: string;
  engine_version: string;
  state: RecommendationState;
  created_at: string;
  updated_at: string;
}

export interface RecommendationDetail extends Recommendation {
  risk_assessment: RiskAssessmentSnapshot | null;
  decision: Decision | null;
}

export interface DecisionResult {
  decision: Decision;
  recommendation: Recommendation;
  superseded_recommendation_ids: string[];
  inspection_frequency_id: string | null;
}

export interface ActionTakenCreateInput {
  description: string;
  outcome_status: ActionOutcomeStatus;
  observed_at?: string | null;
}
