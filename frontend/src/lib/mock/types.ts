export type Role = "viewer" | "metrologist" | "quality_engineer" | "admin" | "auditor";

export interface DemoUser {
  id: string;
  email: string;
  displayName: string;
  role: Role;
}

export type SeriesPattern =
  | "stable"
  | "drift"
  | "shift_after_event"
  | "high_variance"
  | "nok_outlier";

export type Classification = "critical" | "significant" | "standard";

export interface Specification {
  nominal: number;
  lowerTol: number | null;
  upperTol: number | null;
  unit: string;
}

export interface Characteristic {
  id: string;
  partId: string;
  balloonNumber: string;
  name: string;
  characteristicType: string;
  classification: Classification;
  specification: Specification;
  pattern: SeriesPattern;
}

export interface PartNumber {
  id: string;
  code: string;
  name: string;
  productFamily: string;
}

export interface MeasurementPoint {
  measuredAt: string; // ISO date
  value: number;
  deviation: number;
  isOk: boolean;
  sampleIndex: number;
}

export interface ProcessEvent {
  id: string;
  type: "tool_change" | "maintenance" | "material_lot_change" | "machine_adjustment";
  machineCode: string;
  occurredAt: string;
  description: string;
}

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface RiskAssessment {
  characteristicId: string;
  score: number; // 0-100
  level: RiskLevel;
  factors: { label: string; contribution: number }[];
  engineVersion: string;
  computedAt: string;
}

export type RecommendationType =
  | "frequency_increase"
  | "frequency_decrease"
  | "immediate_inspection"
  | "investigate_cause"
  | "post_event_validation";

export type RecommendationState = "pending" | "accepted" | "rejected" | "superseded" | "expired";

export interface Recommendation {
  id: string;
  characteristicId: string;
  type: RecommendationType;
  rationale: string;
  evidence: string[];
  ruleVersion: string;
  state: RecommendationState;
  createdAt: string;
  decidedBy?: string;
  decidedAt?: string;
  decisionComment?: string;
  riskScore: number;
}

export interface MeasurementRunSummary {
  id: string;
  partId: string;
  machineCode: string;
  startedAt: string;
  sampleCount: number;
  nokCount: number;
}

export type ParseStatus = "pending" | "parsing" | "parsed" | "quarantined" | "error";

export interface ImportScenario {
  id: string;
  filename: string;
  description: string;
  partId: string | null; // null => scenario always fails validation
  sampleCount: number;
  willQuarantine: boolean;
  quarantineReason?: string;
}

export interface ImportedFileRecord {
  id: string;
  scenarioId: string;
  filename: string;
  partId: string | null;
  status: ParseStatus;
  uploadedAt: string;
  sha256: string;
  errorDetail?: string;
  runId?: string;
}
