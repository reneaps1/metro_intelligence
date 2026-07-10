import { makeRng } from "./generator";
import type {
  Characteristic,
  DemoUser,
  MeasurementPoint,
  MeasurementRunSummary,
  PartNumber,
  ProcessEvent,
  Recommendation,
  RiskAssessment,
  RiskLevel,
  SeriesPattern,
} from "./types";

// All identifiers are fictitious per docs/seed-data-strategy.md and CLAUDE.md §20 —
// MI-DEMO-* naming, .demo.local emails, invented plant/line/machine codes.
export const DEMO_NOW = new Date("2026-07-09T12:00:00Z");
const DAY_MS = 24 * 60 * 60 * 1000;
const HISTORY_DAYS = 90;
const POINT_INTERVAL_DAYS = 2;

export const DEMO_USERS: DemoUser[] = [
  { id: "u-ana", email: "ana.garcia@demo.local", displayName: "Ana García", role: "metrologist" },
  { id: "u-luis", email: "luis.martinez@demo.local", displayName: "Luis Martínez", role: "quality_engineer" },
  { id: "u-sofia", email: "sofia.reyes@demo.local", displayName: "Sofía Reyes", role: "admin" },
  { id: "u-carlos", email: "carlos.jimenez@demo.local", displayName: "Carlos Jiménez", role: "viewer" },
  { id: "u-maria", email: "maria.lopez@demo.local", displayName: "María López", role: "auditor" },
];

export const PARTS: PartNumber[] = [
  { id: "part-1001", code: "MI-DEMO-1001", name: "Bracket Front Left (Demo)", productFamily: "Suspension Components (Demo)" },
  { id: "part-1002", code: "MI-DEMO-1002", name: "Bracket Front Right (Demo)", productFamily: "Suspension Components (Demo)" },
  { id: "part-1003", code: "MI-DEMO-1003", name: "Control Arm (Demo)", productFamily: "Suspension Components (Demo)" },
];

interface CharacteristicSeed {
  id: string;
  partId: string;
  balloonNumber: string;
  name: string;
  characteristicType: string;
  classification: Characteristic["classification"];
  nominal: number;
  lowerTol: number | null;
  upperTol: number | null;
  unit: string;
  pattern: SeriesPattern;
  seed: number;
}

const CHARACTERISTIC_SEEDS: CharacteristicSeed[] = [
  { id: "char-1001-1", partId: "part-1001", balloonNumber: "1", name: "Bore Diameter A", characteristicType: "diameter", classification: "critical", nominal: 25.4, lowerTol: -0.05, upperTol: 0.05, unit: "mm", pattern: "stable", seed: 1 },
  { id: "char-1001-2", partId: "part-1001", balloonNumber: "2", name: "Mounting Hole Position X", characteristicType: "position", classification: "significant", nominal: 12.0, lowerTol: -0.1, upperTol: 0.1, unit: "mm", pattern: "drift", seed: 2 },
  { id: "char-1001-3", partId: "part-1001", balloonNumber: "3", name: "Flatness Top Face", characteristicType: "flatness", classification: "standard", nominal: 0.0, lowerTol: null, upperTol: 0.08, unit: "mm", pattern: "high_variance", seed: 3 },
  { id: "char-1001-4", partId: "part-1001", balloonNumber: "4", name: "Bore Diameter B", characteristicType: "diameter", classification: "critical", nominal: 18.0, lowerTol: -0.03, upperTol: 0.03, unit: "mm", pattern: "shift_after_event", seed: 4 },
  { id: "char-1002-1", partId: "part-1002", balloonNumber: "1", name: "Bore Diameter A", characteristicType: "diameter", classification: "critical", nominal: 25.4, lowerTol: -0.05, upperTol: 0.05, unit: "mm", pattern: "stable", seed: 5 },
  { id: "char-1002-2", partId: "part-1002", balloonNumber: "2", name: "Mounting Hole Position X", characteristicType: "position", classification: "significant", nominal: 12.0, lowerTol: -0.1, upperTol: 0.1, unit: "mm", pattern: "nok_outlier", seed: 6 },
  { id: "char-1002-3", partId: "part-1002", balloonNumber: "3", name: "Profile Edge", characteristicType: "profile", classification: "standard", nominal: 0.0, lowerTol: -0.06, upperTol: 0.06, unit: "mm", pattern: "stable", seed: 7 },
  { id: "char-1003-1", partId: "part-1003", balloonNumber: "1", name: "Ball Joint Bore", characteristicType: "diameter", classification: "critical", nominal: 32.5, lowerTol: -0.04, upperTol: 0.04, unit: "mm", pattern: "drift", seed: 8 },
  { id: "char-1003-2", partId: "part-1003", balloonNumber: "2", name: "Arm Length", characteristicType: "position", classification: "significant", nominal: 245.0, lowerTol: -0.3, upperTol: 0.3, unit: "mm", pattern: "high_variance", seed: 9 },
  { id: "char-1003-3", partId: "part-1003", balloonNumber: "3", name: "Bushing Bore Flatness", characteristicType: "flatness", classification: "standard", nominal: 0.0, lowerTol: null, upperTol: 0.1, unit: "mm", pattern: "stable", seed: 10 },
];

export const CHARACTERISTICS: Characteristic[] = CHARACTERISTIC_SEEDS.map((c) => ({
  id: c.id,
  partId: c.partId,
  balloonNumber: c.balloonNumber,
  name: c.name,
  characteristicType: c.characteristicType,
  classification: c.classification,
  specification: { nominal: c.nominal, lowerTol: c.lowerTol, upperTol: c.upperTol, unit: c.unit },
  pattern: c.pattern,
}));

const EVENT_DAY_OFFSET = 45; // days into the 90-day history

export const PROCESS_EVENTS: ProcessEvent[] = [
  {
    id: "evt-tool-change-1",
    type: "tool_change",
    machineCode: "CMM-01",
    occurredAt: new Date(DEMO_NOW.getTime() - (HISTORY_DAYS - EVENT_DAY_OFFSET) * DAY_MS).toISOString(),
    description: "Tool change on CMM-01 fixture — Bore Diameter B gauge recalibrated.",
  },
];

function generateSeries(seed: CharacteristicSeed): MeasurementPoint[] {
  const rng = makeRng(seed.seed * 7919 + 13);
  const tolSpan = (seed.upperTol ?? 0.1) - (seed.lowerTol ?? -0.1);
  const points: MeasurementPoint[] = [];
  const pointCount = Math.floor(HISTORY_DAYS / POINT_INTERVAL_DAYS);

  for (let i = 0; i <= pointCount; i++) {
    const dayOffset = HISTORY_DAYS - i * POINT_INTERVAL_DAYS;
    const measuredAt = new Date(DEMO_NOW.getTime() - dayOffset * DAY_MS);
    let deviation: number;

    switch (seed.pattern) {
      case "stable":
        deviation = rng.gaussian(0, tolSpan / 12);
        break;
      case "drift": {
        const progress = i / pointCount;
        const driftTarget = (seed.upperTol ?? tolSpan / 2) * 0.9;
        deviation = rng.gaussian(progress * driftTarget, tolSpan / 14);
        break;
      }
      case "shift_after_event": {
        const afterEvent = dayOffset < HISTORY_DAYS - EVENT_DAY_OFFSET;
        const base = afterEvent ? (seed.upperTol ?? tolSpan / 2) * 0.65 : 0;
        deviation = rng.gaussian(base, tolSpan / 14);
        break;
      }
      case "high_variance":
        deviation = rng.gaussian(0, tolSpan / 5);
        break;
      case "nok_outlier": {
        const isOutlier = i > 0 && i % 13 === 0;
        deviation = isOutlier
          ? (seed.upperTol ?? tolSpan / 2) * (1.4 + rng.next() * 0.6)
          : rng.gaussian(0, tolSpan / 12);
        break;
      }
      default:
        deviation = rng.gaussian(0, tolSpan / 12);
    }

    const value = seed.nominal + deviation;
    const isOk =
      (seed.lowerTol === null || deviation >= seed.lowerTol) &&
      (seed.upperTol === null || deviation <= seed.upperTol);

    points.push({
      measuredAt: measuredAt.toISOString(),
      value: Math.round(value * 1e6) / 1e6,
      deviation: Math.round(deviation * 1e6) / 1e6,
      isOk,
      sampleIndex: i + 1,
    });
  }
  return points;
}

const SERIES_BY_CHARACTERISTIC = new Map<string, MeasurementPoint[]>(
  CHARACTERISTIC_SEEDS.map((seed) => [seed.id, generateSeries(seed)])
);

export function getSeriesForCharacteristic(characteristicId: string): MeasurementPoint[] {
  return SERIES_BY_CHARACTERISTIC.get(characteristicId) ?? [];
}

function levelFromScore(score: number): RiskLevel {
  if (score >= 80) return "critical";
  if (score >= 60) return "high";
  if (score >= 35) return "medium";
  return "low";
}

const PATTERN_BASE_SCORE: Record<SeriesPattern, number> = {
  stable: 15,
  drift: 62,
  shift_after_event: 45,
  high_variance: 72,
  nok_outlier: 58,
};

const PATTERN_FACTORS: Record<SeriesPattern, RiskAssessment["factors"]> = {
  stable: [
    { label: "Proximity to tolerance limit", contribution: 10 },
    { label: "Trend slope", contribution: 5 },
    { label: "Process event correlation", contribution: 0 },
  ],
  drift: [
    { label: "Proximity to tolerance limit", contribution: 35 },
    { label: "Trend slope (drifting toward limit)", contribution: 22 },
    { label: "Historical NOK rate", contribution: 5 },
  ],
  shift_after_event: [
    { label: "Mean shift after tool change", contribution: 30 },
    { label: "Process event correlation", contribution: 12 },
    { label: "Proximity to tolerance limit", contribution: 3 },
  ],
  high_variance: [
    { label: "Process variance (low Cpk)", contribution: 40 },
    { label: "Proximity to tolerance limit", contribution: 20 },
    { label: "Historical NOK rate", contribution: 12 },
  ],
  nok_outlier: [
    { label: "Recent NOK outlier", contribution: 38 },
    { label: "Historical NOK rate", contribution: 15 },
    { label: "Trend slope", contribution: 5 },
  ],
};

export const RISK_ASSESSMENTS: RiskAssessment[] = CHARACTERISTIC_SEEDS.map((seed) => {
  const rng = makeRng(seed.seed * 101 + 3);
  const score = Math.min(97, Math.max(3, Math.round(PATTERN_BASE_SCORE[seed.pattern] + rng.next() * 10 - 5)));
  return {
    characteristicId: seed.id,
    score,
    level: levelFromScore(score),
    factors: PATTERN_FACTORS[seed.pattern],
    engineVersion: "risk-engine-mock@0.1.0",
    computedAt: DEMO_NOW.toISOString(),
  };
});

const RECOMMENDATION_TEMPLATES: Partial<
  Record<SeriesPattern, Pick<Recommendation, "type" | "rationale" | "state">>
> = {
  stable: {
    type: "frequency_decrease",
    rationale: "Cpk has stayed above 1.67 for the last 90 days with no NOK results — inspection frequency can safely decrease.",
    state: "pending",
  },
  drift: {
    type: "investigate_cause",
    rationale: "Measured values show a sustained drift toward the upper tolerance limit over the last 90 days.",
    state: "pending",
  },
  shift_after_event: {
    type: "post_event_validation",
    rationale: "Mean shifted after the CMM-01 tool change on this characteristic — validate the new process center is acceptable.",
    state: "accepted",
  },
  high_variance: {
    type: "frequency_increase",
    rationale: "Process variance is high (Cpk < 1.0) with several points near tolerance limits — increase sampling until stabilized.",
    state: "pending",
  },
  nok_outlier: {
    type: "immediate_inspection",
    rationale: "Isolated NOK outliers detected; recommend immediate inspection of the affected batch.",
    state: "rejected",
  },
};

export const RECOMMENDATIONS: Recommendation[] = CHARACTERISTIC_SEEDS.map((seed, index) => {
  const template = RECOMMENDATION_TEMPLATES[seed.pattern]!;
  const risk = RISK_ASSESSMENTS[index];
  const createdAt = new Date(DEMO_NOW.getTime() - (5 + index) * DAY_MS).toISOString();
  const decided = template.state !== "pending";
  return {
    id: `rec-${seed.id}`,
    characteristicId: seed.id,
    type: template.type,
    rationale: template.rationale,
    evidence: [`risk-assessment:${seed.id}`, `series:${seed.id}:last-90d`],
    ruleVersion: "recommendation-engine-mock@0.1.0",
    state: template.state,
    createdAt,
    decidedBy: decided ? "luis.martinez@demo.local" : undefined,
    decidedAt: decided ? new Date(DEMO_NOW.getTime() - (2 + index) * DAY_MS).toISOString() : undefined,
    decisionComment: decided
      ? template.state === "accepted"
        ? "Reviewed the post-event series — new center is within spec, approving validation."
        : "Reviewed — outliers traced to a mismeasured sample, no action needed."
      : undefined,
    riskScore: risk.score,
  };
});

export const MEASUREMENT_RUNS: MeasurementRunSummary[] = PARTS.map((part, index) => {
  const chars = CHARACTERISTICS.filter((c) => c.partId === part.id);
  const nokCount = chars.reduce((count, c) => {
    const series = getSeriesForCharacteristic(c.id);
    return count + (series.at(-1)?.isOk === false ? 1 : 0);
  }, 0);
  return {
    id: `run-${part.id}-latest`,
    partId: part.id,
    machineCode: index === 2 ? "SCAN-01" : `CMM-0${index + 1}`,
    startedAt: DEMO_NOW.toISOString(),
    sampleCount: chars.length,
    nokCount,
  };
});
