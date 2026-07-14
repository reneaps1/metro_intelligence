import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

// F5.4 (MI-33): mocks the real F4.2 /auth contract (backend/app/api/v1/auth.py)
// so AuthProvider/LoginPage tests exercise the actual request/response shapes
// without a running backend.
const API_BASE_URL = "http://localhost:8000/api/v1";

export const VALID_EMAIL = "sofia.mendez@demo.local";
export const VALID_PASSWORD = "correct-horse-battery-staple";

export const ME_FIXTURE = {
  id: "8f14e45f-ceea-467e-adde-3fb5c8a5f3ba",
  email: VALID_EMAIL,
  display_name: "Sofía Méndez",
  is_active: true,
  roles: ["quality_engineer"],
};

export const handlers = [
  http.post(`${API_BASE_URL}/auth/login`, async ({ request }) => {
    const form = new URLSearchParams(await request.text());
    const username = form.get("username");
    const password = form.get("password");
    if (username === VALID_EMAIL && password === VALID_PASSWORD) {
      return HttpResponse.json({
        access_token: "access-token-1",
        refresh_token: "refresh-token-1",
        token_type: "bearer",
      });
    }
    return HttpResponse.json({ detail: "Invalid email or password." }, { status: 401 });
  }),

  http.get(`${API_BASE_URL}/auth/me`, ({ request }) => {
    const auth = request.headers.get("Authorization");
    if (auth !== "Bearer access-token-1" && auth !== "Bearer access-token-2") {
      return HttpResponse.json({ detail: "Not authenticated" }, { status: 401 });
    }
    return HttpResponse.json(ME_FIXTURE);
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

export const server = setupServer(...handlers);
