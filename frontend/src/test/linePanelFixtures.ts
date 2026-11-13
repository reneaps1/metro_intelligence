import { http, HttpResponse } from "msw";
import type { LineAlarmEvent, LineMoments, LineReplay } from "../lib/line-panel/types";

// IQ-F15: fictitious /line-panel payloads (docs/design/line-quality-panel.md).
// 40 pieces every 2 s on 3 nests: 10 lead pieces (t < 0) and 30 in the window.
// The "stop" replay has a 5-NOK streak whose last piece is the first one of the
// window (t = 0), so the R1 alarm is up as soon as the replay opens.

const API_BASE_URL = "http://localhost:8000/api/v1";
export const LINE_T0 = 1_790_000_000; // window start (epoch s), 06:00 at UTC-5 + 3 h
const SHIFT_START = LINE_T0 - 3 * 3600;

export function makeLineReplay(withStop: boolean): LineReplay {
  const n = 40;
  const lead = 10;
  const t = Array.from({ length: n }, (_, i) => (i - lead) * 2);
  const nok = Array.from({ length: n }, (_, i) => (i % 9 === 4 ? 1 : 0));
  if (withStop) for (let i = 6; i <= 10; i++) nok[i] = 1;
  const run: number[] = [];
  nok.forEach((v, i) => run.push(v ? (run[i - 1] ?? 0) + 1 : 0));
  const alarms: LineAlarmEvent[] = withStop
    ? [
        {
          id: "R1::9010",
          rule: "R1",
          priority: 1,
          key: null,
          raised_index: 10,
          raised_ts: LINE_T0,
          cleared_index: 11,
          cleared_ts: LINE_T0 + 2,
          evidence_from_index: 6,
          evidence_from_ts: LINE_T0 - 8,
          value: 5,
          peak: 5,
          limit: 5,
          nests: [1, 2, 3, 1, 2],
          station: "s1",
        },
      ]
    : [];
  return {
    engine_name: "line_alarm_engine",
    engine_version: "v1-experimental",
    dataset: "demo-synthetic-dimensional",
    dataset_name: "Demo · línea ficticia",
    provenance: "SIMULATED",
    nok_basis: "spec",
    utc_offset_minutes: -300,
    machine: "INY-01",
    line: { nests: [1, 2, 3], mold_cavities: null, stations: [{ key: "s1", name: "Estación ficticia" }] },
    rules: {
      run_limit: 5,
      nest_window: 50,
      nest_factor: 2,
      nest_min_nok: 10,
      rate_window: 200,
      rate_factor: 2,
      rate_limit: 0.2,
      cavity_window: 150,
      cavity_factor: 3,
      cavity_limit: 0.3,
      reference_nok_rate: 0.1,
      clear_fraction: 0.75,
      texts: { R1: "R1", R2: "R2", R3: "R3", R4: "R4" },
    },
    window: { start_ts: LINE_T0, end_ts: LINE_T0 + 3600 },
    lead,
    shifts: [
      { label: "06:00–14:00", start_ts: SHIFT_START, end_ts: SHIFT_START + 8 * 3600 },
      { label: "14:00–22:00", start_ts: SHIFT_START + 8 * 3600, end_ts: SHIFT_START + 16 * 3600 },
    ],
    baseline: {
      pieces: 1000,
      nok: 100,
      by_nest: [
        [1, 334, 30],
        [2, 333, 40],
        [3, 333, 30],
      ],
      by_cavity: [],
      by_station: [["s1", 100]],
      hours: [
        [SHIFT_START, 400, 40],
        [SHIFT_START + 3600, 400, 40],
        [SHIFT_START + 7200, 200, 20],
      ],
    },
    pieces: {
      t,
      nest: t.map((_, i) => (i % 3) + 1),
      cavity: t.map(() => null),
      nok,
      station: nok.map((v) => (v ? 0 : -1)),
    },
    state: {
      run,
      rate: t.map(() => null),
      nest_ratio: t.map(() => null),
      nest_ratio_nest: t.map(() => null),
      cavity_rate: t.map(() => null),
      cavity_worst: t.map(() => null),
    },
    alarms,
  };
}

export const LINE_MOMENTS_FIXTURE: LineMoments = {
  dataset: "demo-synthetic-dimensional",
  dataset_name: "Demo · línea ficticia",
  provenance: "SIMULATED",
  utc_offset_minutes: -300,
  start_ts: LINE_T0 - 86_400,
  end_ts: LINE_T0 + 86_400,
  pieces: 5000,
  reference_nok_rate: 0.1,
  engine_name: "line_alarm_engine",
  engine_version: "v1-experimental",
  moments: [
    { key: "normal-1", kind: "normal", rule: null, key_group: null, raised_ts: LINE_T0 - 7200, peak: 900, label: "Tramo sin alarmas", replay_start_ts: LINE_T0 - 7200 },
    { key: "stop-1", kind: "stop", rule: "R1", key_group: null, raised_ts: LINE_T0, peak: 5, label: "Racha de 5 NOK consecutivas", replay_start_ts: LINE_T0 },
  ],
};

export const linePanelHandlers = [
  http.get(`${API_BASE_URL}/line-panel/moments`, () => HttpResponse.json(LINE_MOMENTS_FIXTURE)),
  http.get(`${API_BASE_URL}/line-panel/replay`, ({ request }) => {
    const start = Number(new URL(request.url).searchParams.get("start"));
    return HttpResponse.json(makeLineReplay(start === LINE_T0));
  }),
];
