import { http, HttpResponse } from "msw";
import { API_BASE_URL } from "../lib/api";
import type { CusumStudy, FailureStudy, ModelLab, ThresholdRow, WaveStudy, WhatIfResult } from "../lib/predictive/types";

// IQ-F7: small, fictitious fixtures for /api/v1/predictive (demo step 6).

const model = (
  key: string,
  name: string,
  family: "ml_tabular" | "deep_learning",
  pr_auc: number,
  c: { tp: number; fp: number; fn: number; tn: number },
) => ({
  key,
  name,
  family,
  roc_auc: 0.85,
  pr_auc,
  recall: c.tp / (c.tp + c.fn),
  precision: c.tp / (c.tp + c.fp),
  confusion: c,
  confusion_approximate: family === "deep_learning",
  note: family === "deep_learning" ? "Matriz reconstruida." : null,
  test_n: 10000,
  positives: c.tp + c.fn,
  flagged: c.tp + c.fp,
  fp_per_tp: c.fp / c.tp,
  alarm_rate: (c.tp + c.fp) / 10000,
  consistent: true,
});

export const MODEL_LAB_FIXTURE: ModelLab = {
  source: "placeholder",
  illustrative: true,
  title: "Ejemplo ilustrativo de estudio ML/DL",
  study_date: "Fecha de ejemplo",
  dataset_description: "Cifras ficticias.",
  split_description: "Partición temporal de ejemplo.",
  variables: 20,
  test_n: 10000,
  test_positives: 60,
  prevalence: 0.006,
  models: [
    model("gb", "Gradient Boosting", "ml_tabular", 0.05, { tp: 50, fp: 2400, fn: 10, tn: 7540 }),
    model("mlp_balanced", "MLP con balanceo de clases", "deep_learning", 0.045, { tp: 51, fp: 3100, fn: 9, tn: 6840 }),
  ],
  best_ml: "gb",
  best_dl: "mlp_balanced",
  dl_beats_ml: false,
  has_threshold_results: false,
  notes: ["Cifras ficticias de ejemplo."],
};

const T0 = Date.UTC(2026, 9, 13) / 1000;
const H = 3600;

export function waveFixture(window: number, threshold: number): WaveStudy {
  return {
    source_type: "SIMULATED",
    engine_name: "nok_wave_engine",
    engine_version: "v1-experimental",
    machine: "INY-01",
    window,
    threshold,
    horizon_groups: 15,
    group_interval_min: 4,
    rule: `Alertar cuando los últimos ${window} grupos inspeccionados suman al menos ${threshold} piezas NOK.`,
    episode_definition: "Episodio = oleada inyectada en el dataset sintético (verdad conocida).",
    summary: {
      episodes: 2,
      anticipated: 0,
      detected: 2,
      missed: 0,
      mean_delay_min: 8,
      mean_remaining_share: 0.95,
      alert_events: 3,
      false_alarm_events: window > 5 ? 4 : 1,
      false_alarms_per_day: 0.14,
    },
    episodes: [
      { start: T0 + 10 * H, end: T0 + 13 * H, groups: 45, status: "detected", first_alert: T0 + 10 * H + 240, delay_min: 4, remaining_share: 0.98 },
      { start: T0 + 30 * H, end: T0 + 32 * H, groups: 30, status: "detected", first_alert: T0 + 30 * H + 720, delay_min: 12, remaining_share: 0.9 },
    ],
    alert_events: [
      { start: T0 + 10 * H + 240, end: T0 + 12 * H, false_alarm: false },
      { start: T0 + 30 * H + 720, end: T0 + 31 * H, false_alarm: false },
      { start: T0 + 20 * H, end: T0 + 20 * H + 240, false_alarm: true },
    ],
    hours: Array.from({ length: 48 }, (_, h) => ({
      ts: T0 + h * H,
      pieces: 180,
      nok_pieces: (h >= 10 && h <= 13) || (h >= 30 && h <= 32) ? 30 : 2,
      in_wave: (h >= 10 && h <= 13) || (h >= 30 && h <= 32),
      alert: h === 10 || h === 20 || h === 30,
    })),
  };
}

export const CUSUM_FIXTURE: CusumStudy = {
  source_type: "SIMULATED",
  engine_name: "cusum_drift_engine",
  engine_version: "v1-experimental",
  machine: "INY-01",
  series: "PinPositionY",
  series_label: "Posición de pin Y · media horaria",
  unit: "mm",
  k_stdevs: 0.5,
  h_stdevs: 4,
  target: 5.6,
  stdev: 0.007,
  k: 0.0035,
  h: 0.028,
  drift_detected: true,
  drift_direction: "upward",
  drift_ts: T0 + 35 * H,
  rationale: "CUSUM drift detected (upward).",
  points: Array.from({ length: 48 }, (_, h) => ({ ts: T0 + h * H, value: 5.6, cusum_high: h > 34 ? 0.03 : 0, cusum_low: 0 })),
};

export function whatIfFixture(moldDelta: number): WhatIfResult {
  const p = moldDelta >= 8 ? 0.43 : 0.0000006;
  return {
    source_type: "SIMULATED",
    hypothetical: true,
    hold_pressure_bar: 620,
    mold_delta_c: moldDelta,
    nest: null,
    worn_insert: false,
    nominal_mm: 12,
    tolerance_mm: 0.05,
    mean_mm: 12 + 0.006 * moldDelta,
    piece_sd_mm: 0.0074,
    nok_probability: p,
    reference_nok_probability: 0.0000006,
    contributions: [
      { label: "Temperatura de molde (Δ)", mm: 0.006 * moldDelta },
      { label: "Presión de mantenimiento", mm: 0 },
      { label: "Nidos (promedio)", mm: 0.0005 },
      { label: "Inserto desgastado (nido 7)", mm: 0 },
    ],
    hold_sweep: [540, 620, 700].map((x) => ({ x, nok_probability: p })),
    mold_sweep: [-5, 0, 15].map((x) => ({ x, nok_probability: x >= 8 ? 0.5 : 0 })),
    mechanism: "Longitud de pines = 12.000 + 0.006·ΔT molde − 0.0006·(P mantenimiento − 620) + offset de nido + ruido.",
    not_modelled: ["El tiempo de ciclo no interviene en el mecanismo sintético: no se ofrece como palanca."],
  };
}

const row = (threshold: number): ThresholdRow => {
  const anticipated = threshold <= 0.5 ? 15 : 9;
  return {
    threshold,
    tp: Math.round(60 * (1 - threshold)),
    fp: Math.round(80 * (1 - threshold)),
    fn: Math.round(60 * threshold),
    tn: 1700,
    precision: 0.4 + threshold * 0.3,
    recall: 1 - threshold,
    episodes_total: 21,
    episodes_anticipated: anticipated,
    mean_lead_h: 2.8,
    false_alarms_per_shift: threshold <= 0.5 ? 0.07 : 0.02,
    alert_events: 30,
  };
};

export const FAILURE_STUDY_FIXTURE: FailureStudy = {
  source_type: "SIMULATED",
  engine_name: "failure_prediction_engine",
  engine_version: "v1-experimental",
  horizon_h: 6,
  split: {
    description: "Partición temporal: 6 semanas de entrenamiento, 3 de prueba.",
    train_rows: 3667,
    test_rows: 1904,
    train_failures: 59,
    test_failures: 21,
    test_positive_rate: 0.063,
  },
  features: [
    { key: "vib_mean_2h", label: "Vibración media (2 h)", coefficient: 1.33 },
    { key: "failures_1h", label: "Fallas en la última hora", coefficient: -0.99 },
  ],
  intercept: -3.1,
  model_pr_auc: 0.399,
  thresholds: Array.from({ length: 19 }, (_, i) => row(Math.round((0.05 + i * 0.05) * 100) / 100)),
  baselines: [
    { key: "last_hour_failure", label: "Alertar si hubo falla en la última hora", pr_auc: 0.063, at_half: { ...row(0.5), episodes_anticipated: 1 } },
    { key: "constant_rate", label: "Tasa constante", pr_auc: 0.063, at_half: { ...row(0.5), episodes_anticipated: 0, precision: null } },
  ],
  timeline: {
    machine: "INY-04",
    points: Array.from({ length: 48 }, (_, i) => ({ hour: 1008 + i, score: i === 20 ? 0.8 : 0.05, vibration: 2.1, current: 45, alarms: 0 })),
    failures: [
      { hour: 1030, has_precursor: true, lead_h: 5 },
      { hour: 1050, has_precursor: false, lead_h: null },
    ],
    maintenance_h: [1040],
  },
  precursor_breakdown: {
    with_precursor_total: 14,
    with_precursor_anticipated: 14,
    without_precursor_total: 7,
    without_precursor_anticipated: 1,
  },
  limitations: ["Datos simulados.", "Requiere validación prospectiva en planta."],
};

export const predictiveHandlers = [
  http.get(`${API_BASE_URL}/predictive/model-lab`, () => HttpResponse.json(MODEL_LAB_FIXTURE)),
  http.get(`${API_BASE_URL}/predictive/nok-waves`, ({ request }) => {
    const q = new URL(request.url).searchParams;
    return HttpResponse.json(waveFixture(Number(q.get("window")), Number(q.get("threshold"))));
  }),
  http.get(`${API_BASE_URL}/predictive/cusum`, () => HttpResponse.json(CUSUM_FIXTURE)),
  http.get(`${API_BASE_URL}/predictive/what-if`, ({ request }) =>
    HttpResponse.json(whatIfFixture(Number(new URL(request.url).searchParams.get("mold_delta")))),
  ),
  http.get(`${API_BASE_URL}/predictive/failure-study`, () => HttpResponse.json(FAILURE_STUDY_FIXTURE)),
];
