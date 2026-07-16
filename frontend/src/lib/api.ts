// F5.4 (MI-33): single HTTP boundary for the real backend (F4.2's /auth
// contract today; every other authenticated call the frontend makes from
// F5.5 onward goes through `apiFetch` too, so token attachment/refresh/error
// mapping stays in one place).
//
// Token storage is intentionally a module-level variable, never
// localStorage/sessionStorage: CLAUDE.md F5.4 acceptance criteria require the
// access token to never touch persistent storage. The backend's /auth/refresh
// returns the refresh token as a normal JSON field rather than an httpOnly
// cookie (see backend/app/api/v1/auth.py), so there is no cookie-based
// alternative to coordinate with -- the refresh token is kept in memory
// alongside the access token. The trade-off: a full page reload always
// requires signing in again. That's acceptable for the demo and is strictly
// safer than persisting either token to disk.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

let accessToken: string | null = null;
let refreshToken: string | null = null;
let sessionExpiredHandler: (() => void) | null = null;

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
}

export function setTokens(tokens: TokenPair | null): void {
  accessToken = tokens?.accessToken ?? null;
  refreshToken = tokens?.refreshToken ?? null;
}

// LM.1: the access token in a WebSocket URL's query string (see
// lib/live-monitor/useLiveSocket.ts) -- a WS handshake from the browser
// can't attach an Authorization header, so it has to read the same in-memory
// token this module already holds for REST calls.
export function getAccessToken(): string | null {
  return accessToken;
}

// Called by AuthProvider so a failed silent refresh (anywhere in the app)
// clears session state exactly once, instead of every call site reimplementing it.
export function onSessionExpired(handler: (() => void) | null): void {
  sessionExpiredHandler = handler;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// Only 4xx codes whose `detail` text is written by our own endpoints
// (CLAUDE.md §18: "Error responses leak no internals") are safe to show
// verbatim. Everything else -- auth failures, rate limiting, upstream/infra
// errors, network failures -- gets a fixed, jargon-free message instead of
// whatever a proxy or the driver put in the body.
const PASSTHROUGH_DETAIL_STATUSES = new Set([400, 404, 409, 422]);

function friendlyMessageFor(status: number): string {
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You don't have permission to do that.";
  if (status === 429) return "Too many attempts. Please wait a moment and try again.";
  if (status >= 500) return "Something went wrong on our end. Please try again.";
  return "Something went wrong. Please try again.";
}

// A 401 means two different things depending on context: on an
// already-authenticated call it means "your session died" (generic message,
// handled by the refresh/expiry branch in `request` before this function is
// ever reached). On `skipAuth` calls -- i.e. /auth/login itself -- there is
// no session to expire; it means "wrong credentials", and the backend's own
// detail text for that ("Invalid email or password.") is deliberately
// user-safe and anti-enumeration, so it's fine to show verbatim.
async function readErrorMessage(response: Response, allowAuthDetail: boolean): Promise<string> {
  const passthrough = PASSTHROUGH_DETAIL_STATUSES.has(response.status) || (response.status === 401 && allowAuthDetail);
  if (passthrough) {
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.length > 0) {
        return body.detail;
      }
      // A handful of endpoints (e.g. duplicate-import 409) return a structured
      // detail (`{message, ...}`) instead of a plain string so the caller can
      // also read the extra fields -- the message itself is still
      // backend-authored, user-safe text.
      if (
        body.detail &&
        typeof body.detail === "object" &&
        "message" in body.detail &&
        typeof (body.detail as { message: unknown }).message === "string"
      ) {
        return (body.detail as { message: string }).message;
      }
    } catch {
      // fall through to the generic message below
    }
  }
  return friendlyMessageFor(response.status);
}

let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return false;
    const data = (await response.json()) as { access_token: string; refresh_token: string };
    setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token });
    return true;
  } catch {
    return false;
  }
}

function refreshTokensOnce(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = refreshTokens().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

interface FetchOptions extends RequestInit {
  /** Skip attaching the Authorization header and skip the 401-refresh retry (login itself). */
  skipAuth?: boolean;
}

async function request<T>(path: string, options: FetchOptions = {}, isRetry = false): Promise<T> {
  const { skipAuth = false, ...init } = options;
  const headers = new Headers(init.headers);
  if (!skipAuth && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  // FormData bodies (file uploads) must NOT get an explicit Content-Type --
  // the browser sets `multipart/form-data; boundary=...` itself, and
  // overriding it here would drop the boundary and break parsing server-side.
  if (init.body !== undefined && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Unable to reach the server. Check your connection and try again.");
  }

  if (response.status === 401 && !skipAuth && !isRetry) {
    const refreshed = await refreshTokensOnce();
    if (refreshed) {
      return request<T>(path, options, true);
    }
    setTokens(null);
    sessionExpiredHandler?.();
    throw new ApiError(401, friendlyMessageFor(401));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response, skipAuth));
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface LoginResult {
  accessToken: string;
  refreshToken: string;
}

export async function loginRequest(email: string, password: string): Promise<LoginResult> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const data = await request<{ access_token: string; refresh_token: string }>("/auth/login", {
    method: "POST",
    // Sent as a plain string (not the URLSearchParams instance) -- passing
    // the instance itself as a fetch body hits a cross-realm `instanceof`
    // check in some fetch implementations (observed under Vitest/jsdom).
    body: form.toString(),
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    skipAuth: true,
  });
  return { accessToken: data.access_token, refreshToken: data.refresh_token };
}

export async function logoutRequest(): Promise<void> {
  if (!refreshToken) return;
  try {
    await request<void>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    // Best-effort server-side revocation; the client always clears local
    // session state regardless (see AuthProvider.logout).
  }
}

export interface MeResponse {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  roles: string[];
}

export function meRequest(): Promise<MeResponse> {
  return request<MeResponse>("/auth/me", { method: "GET" });
}

/** Generic authenticated request helper for F5.5+ screens. */
export function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  return request<T>(path, options);
}
