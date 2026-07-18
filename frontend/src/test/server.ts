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

export const server = setupServer(
  ...handlers,
  ...catalogHandlers,
  ...recommendationsHandlers,
  ...liveMonitorHandlers,
);
