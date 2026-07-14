import { afterEach, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/server";
import { apiFetch, ApiError, onSessionExpired, setTokens, type MeResponse } from "./api";

const API_BASE_URL = "http://localhost:8000/api/v1";

afterEach(() => {
  setTokens(null);
  onSessionExpired(null);
});

describe("apiFetch", () => {
  it("transparently refreshes an expired access token and retries the original call once", async () => {
    setTokens({ accessToken: "stale-access-token", refreshToken: "refresh-token-1" });

    const me = await apiFetch<MeResponse>("/auth/me");

    expect(me.email).toBe("sofia.mendez@demo.local");
  });

  it("clears the session and notifies exactly once when the refresh token is also invalid", async () => {
    setTokens({ accessToken: "stale-access-token", refreshToken: "refresh-token-BAD" });
    let notifications = 0;
    onSessionExpired(() => {
      notifications += 1;
    });

    await expect(apiFetch<MeResponse>("/auth/me")).rejects.toThrow(ApiError);

    expect(notifications).toBe(1);
  });

  it("does not loop refreshing forever if the refreshed token is still rejected", async () => {
    let refreshCalls = 0;
    server.use(
      http.post(`${API_BASE_URL}/auth/refresh`, () => {
        refreshCalls += 1;
        return HttpResponse.json({
          access_token: "still-stale",
          refresh_token: "refresh-token-1",
          token_type: "bearer",
        });
      }),
    );
    setTokens({ accessToken: "stale-access-token", refreshToken: "refresh-token-1" });

    await expect(apiFetch<MeResponse>("/auth/me")).rejects.toThrow(ApiError);

    expect(refreshCalls).toBe(1);
  });

  it("maps a 500 to a clean message with no backend internals", async () => {
    server.use(
      http.get(`${API_BASE_URL}/auth/me`, () =>
        HttpResponse.json({ detail: "Traceback (most recent call last): ..." }, { status: 500 }),
      ),
    );
    setTokens({ accessToken: "access-token-1", refreshToken: "refresh-token-1" });

    await expect(apiFetch<MeResponse>("/auth/me")).rejects.toMatchObject({
      message: expect.not.stringContaining("Traceback"),
    });
  });
});
