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

const CREDENTIALS: Record<string, { password: string; accessToken: string }> = {
  [VALID_EMAIL]: { password: VALID_PASSWORD, accessToken: "access-token-1" },
  [ADMIN_EMAIL]: { password: ADMIN_PASSWORD, accessToken: "access-token-admin" },
};

const ME_BY_TOKEN: Record<string, typeof ME_FIXTURE> = {
  "access-token-1": ME_FIXTURE,
  "access-token-2": ME_FIXTURE,
  "access-token-admin": ME_ADMIN_FIXTURE,
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
  http.get(`${API_BASE_URL}/catalog/characteristics/:id/specifications`, () =>
    HttpResponse.json([ACTIVE_SPEC_FIXTURE, CLOSED_SPEC_FIXTURE]),
  ),
];

export const server = setupServer(...handlers, ...catalogHandlers);
