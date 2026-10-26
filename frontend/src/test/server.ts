import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

// F5.4 (MI-33): mocks the real F4.2 /auth contract (backend/app/api/v1/auth.py)
// so AuthProvider/LoginPage tests exercise the actual request/response shapes
// without a running backend.
const API_BASE_URL = "http://localhost:8000/api/v1";

export const VALID_EMAIL = "sofia.mendez@demo.local";
export const VALID_PASSWORD = "correct-horse-battery-staple";
export const ADMIN_EMAIL = "luis.torres@demo.local";
export const ADMIN_PASSWORD = "admin-password-for-tests-only";
export const METROLOGIST_EMAIL = "ana.garcia@demo.local";
export const METROLOGIST_PASSWORD = "metrologist-password-for-tests-only";
export const AUDITOR_EMAIL = "carlos.ruiz@demo.local";
export const AUDITOR_PASSWORD = "auditor-password-for-tests-only";

export const ME_FIXTURE = {
  id: "8f14e45f-ceea-467e-adde-3fb5c8a5f3ba",
  email: VALID_EMAIL,
  display_name: "Sofía Méndez",
  is_active: true,
  roles: ["quality_engineer"],
};

export const ME_ADMIN_FIXTURE = {
  id: "9f14e45f-ceea-467e-adde-3fb5c8a5f3bb",
  email: ADMIN_EMAIL,
  display_name: "Luis Torres",
  is_active: true,
  roles: ["admin"],
};

export const ME_METROLOGIST_FIXTURE = {
  id: "af14e45f-ceea-467e-adde-3fb5c8a5f3bc",
  email: METROLOGIST_EMAIL,
  display_name: "Ana García",
  is_active: true,
  roles: ["metrologist"],
};

export const ME_AUDITOR_FIXTURE = {
  id: "bf14e45f-ceea-467e-adde-3fb5c8a5f3bd",
  email: AUDITOR_EMAIL,
  display_name: "Carlos Ruiz",
  is_active: true,
  roles: ["auditor"],
};

const CREDENTIALS: Record<string, { password: string; accessToken: string }> = {
  [VALID_EMAIL]: { password: VALID_PASSWORD, accessToken: "access-token-1" },
  [ADMIN_EMAIL]: { password: ADMIN_PASSWORD, accessToken: "access-token-admin" },
  [METROLOGIST_EMAIL]: { password: METROLOGIST_PASSWORD, accessToken: "access-token-metrologist" },
  [AUDITOR_EMAIL]: { password: AUDITOR_PASSWORD, accessToken: "access-token-auditor" },
};

const ME_BY_TOKEN: Record<string, typeof ME_FIXTURE> = {
  "access-token-1": ME_FIXTURE,
  "access-token-2": ME_FIXTURE,
  "access-token-admin": ME_ADMIN_FIXTURE,
  "access-token-metrologist": ME_METROLOGIST_FIXTURE,
  "access-token-auditor": ME_AUDITOR_FIXTURE,
};

export const handlers = [
  http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
    const form = new URLSearchParams(await request.text());
    const username = form.get("username") ?? "";
    const password = form.get("password");
    const credentials = CREDENTIALS[username];
    if (credentials && credentials.password === password) {
      return HttpResponse.json({
        access_token: credentials.accessToken,
        refresh_token: "refresh-token-1",
        token_type: "bearer",
      });
    }
    return HttpResponse.json({ detail: "Invalid email or password." }, { status: 401 });
  }),

  http.get(`${API_BASE_URL}/auth/me`, ({ request }) => {
    const auth = request.headers.get("Authorization")?.replace("Bearer ", "") ?? "";
    const me = ME_BY_TOKEN[auth];
    if (!me) {
      return HttpResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }
    return HttpResponse.json(me);
  }),

  http.post(`${API_BASE_URL}/auth/refresh`, async ({ request }) => {
    const body = (await request.json()) as { refresh_token: string };
    if (body.refresh_token === "refresh-token-1") {
      return HttpResponse.json({
        access_token: "access-token-2",
        refresh_token: "refresh-token-2",
        token_type: "bearer",
      });
    }
    return HttpResponse.json({ detail: "Refresh token revoked." }, { status: 401 });
  }),

  http.post(`${API_BASE_URL}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
];

// F5.5 (MI-34): fixtures mirroring F4.4's /catalog contract shape (Decimal
// fields as strings -- see backend/app/schemas/catalog.py).
export const FAMILY_FIXTURE = {
  id: "11111111-1111-1111-1111-111111111111",
  code: "MI-DEMO-FAM-1",
  name: "Bracket Family (Demo)",
  description: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const PART_FIXTURE = {
  id: "22222222-2222-2222-2222-222222222222",
  product_family_id: FAMILY_FIXTURE.id,
  code: "MI-DEMO-1001",
  name: "Bracket Front Left (Demo)",
  description: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

export const CLASSIFICATION_FIXTURE = {
  id: "33333333-3333-3333-3333-333333333333",
  code: "critical",
  name: "Critical (CC)",
  description: null,
  created_at: "2026-01-01T00:00:00Z",
};

export const ACTIVE_SPEC_FIXTURE = {
  id: "44444444-4444-4444-4444-444444444444",
  characteristic_id: "55555555-5555-5555-5555-555555555555",
  nominal: "10.000",
  lower_tol: "-0.050",
  upper_tol: "0.050",
  unit: "mm",
  valid_from: "2026-01-01T00:00:00Z",
  valid_to: null,
  created_at: "2026-01-01T00:00:00Z",
};

export const CLOSED_SPEC_FIXTURE = {
  id: "66666666-6666-6666-6666-666666666666",
  characteristic_id: "55555555-5555-5555-5555-555555555555",
  nominal: "10.000",
  lower_tol: "-0.100",
  upper_tol: "0.100",
  unit: "mm",
  valid_from: "2025-06-01T00:00:00Z",
  valid_to: "2026-01-01T00:00:00Z",
  created_at: "2025-06-01T00:00:00Z",
};

export const CHARACTERISTIC_FIXTURE = {
  id: ACTIVE_SPEC_FIXTURE.characteristic_id,
  part_number_id: PART_FIXTURE.id,
  balloon_number: "12",
  name: "Bore Diameter A",
  characteristic_type: "diameter",
  unit: "mm",
  classification_id: CLASSIFICATION_FIXTURE.id,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  active_specification: ACTIVE_SPEC_FIXTURE,
};

export const catalogHandlers = [
  http.get(`${API_BASE_URL}/catalog/product-families`, () =>
    HttpResponse.json({ items: [FAMILY_FIXTURE], total: 1, page: 1, page_size: 200 }),
  ),
  http.get(`${API_BASE_URL}/catalog/characteristic-classifications`, () =>
    HttpResponse.json({ items: [CLASSIFICATION_FIXTURE], total: 1, page: 1, page_size: 200 }),
  ),
  http.get(`${API_BASE_URL}/catalog/part-numbers`, () =>
    HttpResponse.json({ items: [PART_FIXTURE], total: 1, page: 1, page_size: 100 }),
  ),
  http.get(`${API_BASE_URL}/catalog/part-numbers/:id`, ({ params }) => {
    if (params.id !== PART_FIXTURE.id) {
      return HttpResponse.json({ detail: "Part number not found." }, { status: 404 });
    }
    return HttpResponse.json(PART_FIXTURE);
  }),
  http.get(`${API_BASE_URL}/catalog/characteristics`, () =>
    HttpResponse.json({ items: [CHARACTERISTIC_FIXTURE], total: 1, page: 1, page_size: 200 }),
  ),
  http.get(`${API_BASE_URL}/catalog/characteristics/:id`, ({ params }) => {
    if (params.id !== CHARACTERISTIC_FIXTURE.id) {
      return HttpResponse.json({ detail: "Characteristic not found." }, { status: 404 });
    }
    return HttpResponse.json(CHARACTERISTIC_FIXTURE);
  }),
  http.get(`${API_BASE_URL}/catalog/characteristics/:id/specifications`, () =>
    HttpResponse.json([ACTIVE_SPEC_FIXTURE, CLOSED_SPEC_FIXTURE]),
  ),
];

// F5.9 (MI-38): fixtures mirroring F4.8's /recommendations and /decisions
// contract shape (backend/app/schemas/intelligence.py).
export const RISK_ASSESSMENT_FIXTURE = {
  id: "77777777-7777-7777-7777-777777777777",
  score: 62,
  level: "high",
  factors: { trend: "drifting", nok_rate: "0.08" },
  engine_name: "risk_engine",
  engine_version: "v0.1",
  computed_at: "2026-07-01T00:00:00Z",
};

export const REC_PENDING_FIXTURE = {
  id: "88888888-8888-8888-8888-888888888888",
  characteristic_id: CHARACTERISTIC_FIXTURE.id,
  recommendation_type: "frequency_increase",
  rationale: "Trend approaching upper tolerance with rising variance.",
  evidence: { run_ids: ["r1", "r2"] },
  engine_name: "adaptive_inspection_engine",
  engine_version: "v0.1",
  state: "pending",
  created_at: "2026-07-02T00:00:00Z",
  updated_at: "2026-07-02T00:00:00Z",
};

export const REC_ACCEPTED_FIXTURE = {
  ...REC_PENDING_FIXTURE,
  id: "99999999-9999-9999-9999-999999999999",
  recommendation_type: "frequency_decrease",
  rationale: "Process has stabilized; variance dropped for six consecutive runs.",
  state: "accepted",
};

export const recommendationsHandlers = [
  http.get(`${API_BASE_URL}/recommendations`, ({ request }) => {
    const url = new URL(request.url);
    const state = url.searchParams.get("state");
    const items = [REC_PENDING_FIXTURE, REC_ACCEPTED_FIXTURE].filter(
      (item) => !state || item.state === state,
    );
    return HttpResponse.json({ items, total: items.length, page: 1, page_size: 100 });
  }),
  http.get(`${API_BASE_URL}/recommendations/:id`, ({ params }) => {
    const base = [REC_PENDING_FIXTURE, REC_ACCEPTED_FIXTURE].find((item) => item.id === params.id);
    if (!base) {
      return HttpResponse.json({ detail: "Recommendation not found." }, { status: 404 });
    }
    return HttpResponse.json({
      ...base,
      risk_assessment: RISK_ASSESSMENT_FIXTURE,
      decision:
        base.state === "accepted"
          ? {
              id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              recommendation_id: base.id,
              decided_by_user_id: ME_FIXTURE.id,
              action: "accepted",
              comment: "Matches the observed drift.",
              decided_at: "2026-07-03T00:00:00Z",
              actions_taken: [],
            }
          : null,
    });
  }),
  http.post(`${API_BASE_URL}/recommendations/:id/decision`, async ({ request, params }) => {
    const body = (await request.json()) as { action: "accepted" | "rejected"; comment: string };
    return HttpResponse.json({
      decision: {
        id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        recommendation_id: params.id,
        decided_by_user_id: ME_FIXTURE.id,
        action: body.action,
        comment: body.comment,
        decided_at: "2026-07-04T00:00:00Z",
        actions_taken: [],
      },
      recommendation: { ...REC_PENDING_FIXTURE, id: params.id, state: body.action },
      superseded_recommendation_ids: [],
      inspection_frequency_id: null,
    });
  }),
  http.post(`${API_BASE_URL}/decisions/:id/actions`, async ({ request }) => {
    const body = (await request.json()) as { description: string; outcome_status: string };
    return HttpResponse.json(
      {
        id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
        description: body.description,
        outcome_status: body.outcome_status,
        observed_at: null,
        created_at: "2026-07-05T00:00:00Z",
      },
      { status: 201 },
    );
  }),
];

// LM.3 (docs/tasks/LM3-live-monitor-presenter-controls.md): fixture for the
// scenario-candidates lookup, mirroring backend/app/schemas/live_monitor.py.
// Uses a characteristic id distinct from CHARACTERISTIC_FIXTURE so tests can
// tell "the default mix" and "a scenario's candidates" apart.
export const SCENARIO_CHARACTERISTIC_ID = "77777777-8888-9999-0000-111111111111";

// LM.4 (docs/tasks/LM4-live-monitor-deep-dive.md): fixtures mirroring F4.6's
// /series and the new /capability-history (backend/app/schemas/measurements.py).
export const SERIES_FIXTURE = {
  characteristic_id: CHARACTERISTIC_FIXTURE.id,
  unit: "mm",
  total_points: 3,
  returned_points: 3,
  downsampled: false,
  points: [
    {
      result_id: "r1",
      measured_at: "2026-01-01T00:00:00Z",
      value: "10.010",
      deviation: "0.010",
      is_ok: true,
      sample_index: 0,
      specification: {
        id: ACTIVE_SPEC_FIXTURE.id,
        nominal: "10.000",
        lower_tol: "-0.050",
        upper_tol: "0.050",
        unit: "mm",
        valid_from: "2026-01-01T00:00:00Z",
        valid_to: null,
      },
    },
    {
      result_id: "r2",
      measured_at: "2026-01-02T00:00:00Z",
      value: "9.990",
      deviation: "-0.010",
      is_ok: true,
      sample_index: 1,
      specification: {
        id: ACTIVE_SPEC_FIXTURE.id,
        nominal: "10.000",
        lower_tol: "-0.050",
        upper_tol: "0.050",
        unit: "mm",
        valid_from: "2026-01-01T00:00:00Z",
        valid_to: null,
      },
    },
    {
      result_id: "r3",
      measured_at: "2026-01-03T00:00:00Z",
      value: "10.020",
      deviation: "0.020",
      is_ok: true,
      sample_index: 2,
      specification: {
        id: ACTIVE_SPEC_FIXTURE.id,
        nominal: "10.000",
        lower_tol: "-0.050",
        upper_tol: "0.050",
        unit: "mm",
        valid_from: "2026-01-01T00:00:00Z",
        valid_to: null,
      },
    },
  ],
};

export const CAPABILITY_HISTORY_FIXTURE = {
  characteristic_id: CHARACTERISTIC_FIXTURE.id,
  unit: "mm",
  window_size: 20,
  windows: [
    {
      window_start: "2026-01-01T00:00:00Z",
      window_end: "2026-01-03T00:00:00Z",
      point_count: 3,
      cpk: "1.8",
      center_line: "10.007",
      ucl: "10.05",
      lcl: "9.96",
      engine_name: "spc_engine",
      engine_version: "v1",
      nominal: "10.000",
    },
  ],
};

// Live Monitor alarm fix (2026-07): default handler returns no open alerts
// so every existing Live Monitor test (which doesn't care about alarms)
// keeps passing without knowing about this endpoint -- tests that DO care
// override it with `server.use(...)`.
export const ALERT_FIXTURE = {
  id: "cccccccc-dddd-eeee-ffff-000000000001",
  characteristic_id: CHARACTERISTIC_FIXTURE.id,
  severity: "warning",
  trigger_type: "compliance_violation",
  trigger_id: "cccccccc-dddd-eeee-ffff-000000000002",
  message: "0.150 mm above the upper tolerance limit.",
  rationale: "0.150 mm above the upper tolerance limit.",
  computed_inputs: { value: "10.15", deviation: "0.15" },
  engine_name: "alarm_rules_engine",
  engine_version: "v1",
  created_at: "2026-01-05T00:00:00Z",
  delivered_at: "2026-01-05T00:00:00Z",
  acknowledged_at: null,
  acknowledged_by_user_id: null,
};

// EXPERIMENTAL (Thompson-Sampling adaptive sampling frequency recommender):
// fixture mirroring SamplingRecommendation (backend/app/schemas/measurements.py).
// Default has no conflicts -- tests that care override with server.use(...).
export const SAMPLING_RECOMMENDATION_FIXTURE = {
  characteristic_id: CHARACTERISTIC_FIXTURE.id,
  recommended_frequency: 20,
  current_cpk: 1.8,
  cpk_trend: "stable",
  confidence: 0.75,
  windows_analyzed: 8,
  conflicting_recommendations: null,
};

export const liveMonitorHandlers = [
  http.get(`${API_BASE_URL}/characteristics/scenario-candidates`, ({ request }) => {
    const url = new URL(request.url);
    const scenario = url.searchParams.get("scenario") ?? "";
    return HttpResponse.json({
      scenario,
      candidate_pool_size: 1,
      characteristic_ids: [SCENARIO_CHARACTERISTIC_ID],
    });
  }),
  http.get(`${API_BASE_URL}/characteristics/:id/series`, () => HttpResponse.json(SERIES_FIXTURE)),
  http.get(`${API_BASE_URL}/characteristics/:id/capability-history`, () =>
    HttpResponse.json(CAPABILITY_HISTORY_FIXTURE),
  ),
  // Phase 13 preview (CLAUDE.md §22) -- default fixture has too little
  // history for the CUSUM engine to run, mirroring CAPABILITY_HISTORY_FIXTURE.
  http.get(`${API_BASE_URL}/characteristics/:id/experimental-drift`, () => HttpResponse.json(null)),
  // EXPERIMENTAL (Thompson-Sampling adaptive sampling frequency recommender).
  http.get(`${API_BASE_URL}/characteristics/:id/sampling-recommendation`, () =>
    HttpResponse.json(SAMPLING_RECOMMENDATION_FIXTURE),
  ),
  http.get(`${API_BASE_URL}/alerts`, () => HttpResponse.json({ items: [], total: 0, page: 1, page_size: 50 })),
  http.post(`${API_BASE_URL}/alerts/:id/acknowledge`, ({ params }) =>
    HttpResponse.json({
      ...ALERT_FIXTURE,
      id: params.id,
      acknowledged_at: "2026-01-06T00:00:00Z",
      acknowledged_by_user_id: ME_FIXTURE.id,
    }),
  ),
];

// IQ-F1: /meta defaults to the metrology edition so every pre-existing test
// sees the original navigation; industrial tests override with server.use(...).
export const META_METROLOGY_FIXTURE = { edition: "metrology", client_label: null, modules: [] };
export const META_INDUSTRIAL_FIXTURE = {
  edition: "industrial",
  client_label: "Cliente demo",
  modules: ["industrial_demo", "industrial_signals"],
};

export const metaHandlers = [http.get(`${API_BASE_URL}/meta`, () => HttpResponse.json(META_METROLOGY_FIXTURE))];

export function industrialMetaHandler() {
  return http.get(`${API_BASE_URL}/meta`, () => HttpResponse.json(META_INDUSTRIAL_FIXTURE));
}

// IQ-F2: fixtures mirroring backend/app/schemas/industrial_signals.py.
const SIGNAL_LEAF = (
  machine: string,
  key: string,
  name: string,
  unit: string,
  valueType: string,
  causalImposed = false,
) => ({
  id: `L1.${machine}.${key}`,
  name,
  node_type: "signal",
  children: [],
  signal: {
    signal_id: `L1.${machine}.${key}`,
    key,
    machine_code: machine,
    name,
    unit,
    value_type: valueType,
    sampling: "continuous",
    rate_hz: 1,
    informative: true,
    description: name,
    source_type: "SIMULATED",
    causal_imposed: causalImposed,
  },
});

export const SIGNAL_TREE_FIXTURE = {
  source_type: "SIMULATED",
  generator_version: "process-sim-1.0.0",
  root: {
    id: "PLANTA-DEMO",
    name: "Planta demo (ficticia)",
    node_type: "plant",
    signal: null,
    children: [
      {
        id: "L1.INY-01",
        name: "Inyectora 01",
        node_type: "machine",
        signal: null,
        children: [
          {
            id: "L1.INY-01.temperatures",
            name: "Temperaturas",
            node_type: "group",
            signal: null,
            children: [SIGNAL_LEAF("INY-01", "mold_temp", "Temperatura de molde", "°C", "analog")],
          },
          {
            id: "L1.INY-01.pressures",
            name: "Presiones",
            node_type: "group",
            signal: null,
            children: [
              SIGNAL_LEAF("INY-01", "injection_pressure", "Presión de inyección", "bar", "analog"),
              SIGNAL_LEAF("INY-01", "holding_pressure", "Presión de mantenimiento (media por ciclo)", "bar", "analog"),
            ],
          },
          {
            id: "L1.INY-01.state",
            name: "Estado de máquina",
            node_type: "group",
            signal: null,
            children: [SIGNAL_LEAF("INY-01", "alarm", "Alarma activa", "0/1", "digital")],
          },
          {
            id: "L1.INY-01.quality_sim",
            name: "Calidad sintética (Vista B · causalidad impuesta)",
            node_type: "group",
            signal: null,
            children: [SIGNAL_LEAF("INY-01", "dim_pins_length", "Longitud de pin (sintética)", "mm", "analog", true)],
          },
        ],
      },
    ],
  },
};

const SCENARIO_WINDOW = { start: "2026-10-20T06:00:00Z", end: "2026-10-20T14:00:00Z" };

export const SCENARIOS_FIXTURE = {
  source_type: "SIMULATED",
  generator_version: "process-sim-1.0.0",
  items: [
    { id: "normal", name: "Operación normal estable", description: "Referencia.", event_count: 1, ...SCENARIO_WINDOW },
    { id: "thermal_drift", name: "Deriva térmica del molde", description: "Molde +8 °C.", event_count: 2, ...SCENARIO_WINDOW },
  ],
};

const EVENTS_BY_SCENARIO: Record<string, { label: string; start: string; severity: string; event_type: string }[]> = {
  normal: [
    { label: "Cambio de lote de material", start: "2026-10-20T08:00:00Z", severity: "info", event_type: "batch_change" },
  ],
  thermal_drift: [
    { label: "Cambio de lote de material", start: "2026-10-20T08:00:00Z", severity: "info", event_type: "batch_change" },
    { label: "Alarma: temperatura de molde > 60 °C", start: "2026-10-20T10:52:30Z", severity: "critical", event_type: "alarm" },
  ],
};

export const industrialSignalsHandlers = [
  http.get(`${API_BASE_URL}/industrial-signals/tree`, () => HttpResponse.json(SIGNAL_TREE_FIXTURE)),
  http.get(`${API_BASE_URL}/industrial-signals/scenarios`, () => HttpResponse.json(SCENARIOS_FIXTURE)),
  http.get(`${API_BASE_URL}/industrial-signals/events`, ({ request }) => {
    const scenario = new URL(request.url).searchParams.get("scenario") ?? "";
    const items = (EVENTS_BY_SCENARIO[scenario] ?? []).map((event, index) => ({
      id: `${scenario}-${index}`,
      scenario_id: scenario,
      machine_code: "INY-01",
      end: null,
      signal_ids: [],
      ...event,
    }));
    return HttpResponse.json({ scenario_id: scenario, source_type: "SIMULATED", items });
  }),
  // IQ-F3: three points per requested signal across the requested window
  // (value = 100 + index), enough to exercise cursors, stats and tracks.
  http.get(`${API_BASE_URL}/industrial-signals/series`, ({ request }) => {
    const url = new URL(request.url);
    const ids = (url.searchParams.get("signals") ?? "").split(",").filter(Boolean);
    const start = Date.parse(url.searchParams.get("start") ?? SCENARIO_WINDOW.start);
    const end = Date.parse(url.searchParams.get("end") ?? SCENARIO_WINDOW.end);
    const mid = (start + end) / 2;
    return HttpResponse.json({
      scenario_id: url.searchParams.get("scenario"),
      source_type: "SIMULATED",
      generator_version: "process-sim-1.1.0",
      start: new Date(start).toISOString(),
      end: new Date(end).toISOString(),
      series: ids.map((id, i) => ({
        signal_id: id,
        name: id,
        unit: "u",
        value_type: "analog",
        sampling: "continuous",
        native_points: 3,
        returned_points: 3,
        downsampled: false,
        mode: "raw",
        points: [
          [start, 100 + i],
          [mid, 110 + i],
          [end, 120 + i],
        ],
      })),
    });
  }),
  http.get(`${API_BASE_URL}/industrial-signals/correlation`, ({ request }) => {
    const url = new URL(request.url);
    const mode = url.searchParams.get("mode") ?? "cycle";
    const x = url.searchParams.get("x") ?? "";
    const y = url.searchParams.get("y") ?? "";
    const causal = y.endsWith("dim_pins_length") || x.endsWith("dim_pins_length");
    return HttpResponse.json({
      scenario_id: url.searchParams.get("scenario"),
      source_type: "SIMULATED",
      generator_version: "process-sim-1.1.0",
      x: { signal_id: x, name: "X", unit: "bar", causal_imposed: false },
      y: { signal_id: y, name: "Y", unit: "mm", causal_imposed: causal },
      mode,
      lag: Number(url.searchParams.get("lag") ?? 0),
      lag_unit: mode === "cycle" ? "cycles" : "s",
      start: SCENARIO_WINDOW.start,
      end: SCENARIO_WINDOW.end,
      n: 983,
      pearson_r: -0.914,
      slope: -0.000592,
      intercept: 12.37,
      r_squared: 0.835,
      points: [
        [560, 12.03],
        [620, 12.0],
      ],
      lag_scan:
        mode === "cycle"
          ? [
              { lag: -1, n: 982, pearson_r: -0.1 },
              { lag: 0, n: 983, pearson_r: -0.914 },
              { lag: 1, n: 982, pearson_r: -0.1 },
            ]
          : [
              { lag: 0, n: 600, pearson_r: -0.01 },
              { lag: 300, n: 590, pearson_r: -0.31 },
            ],
      best_lag: mode === "cycle" ? 0 : 300,
      causal_imposed: causal,
    });
  }),
];

export const server = setupServer(
  ...handlers,
  ...catalogHandlers,
  ...recommendationsHandlers,
  ...liveMonitorHandlers,
  ...metaHandlers,
  ...industrialSignalsHandlers,
);
