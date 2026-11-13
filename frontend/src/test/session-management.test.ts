import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/store/useAuthStore";

describe("Phase 8B - Secure Session & Storage Policy", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    useAuthStore.getState().clearAuth();
  });

  it("never persists refresh token to localStorage", () => {
    const mockUser = {
      id: "u-secure",
      email: "secure@sentinelvoice.io",
      full_name: "Security Lead",
      is_active: true,
      is_verified: true,
      roles: ["USER" as const],
      created_at: "2026-11-13T10:00:00Z",
    };

    useAuthStore.getState().setAuth(mockUser, "jwt-shortlived-access-123", "opaque-refresh-456");

    // In-memory / sessionStorage checks
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().accessToken).toBe("jwt-shortlived-access-123");
    expect(sessionStorage.getItem("sentinel_access_token")).toBe("jwt-shortlived-access-123");

    // Security invariant: localStorage MUST NOT have refresh token
    expect(localStorage.getItem("sentinel_refresh_token")).toBeNull();
    expect(localStorage.getItem("sentinel_access_token")).toBeNull();
  });

  it("clearAuth sweeps both sessionStorage and legacy localStorage tokens", () => {
    sessionStorage.setItem("sentinel_access_token", "sample-access");
    sessionStorage.setItem("sentinel_refresh_fallback", "sample-refresh");
    sessionStorage.setItem("sentinel_user", JSON.stringify({ email: "test" }));
    localStorage.setItem("sentinel_access_token", "legacy-token");
    localStorage.setItem("sentinel_refresh_token", "legacy-refresh");

    useAuthStore.getState().clearAuth();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().accessToken).toBeNull();

    expect(sessionStorage.getItem("sentinel_access_token")).toBeNull();
    expect(sessionStorage.getItem("sentinel_refresh_fallback")).toBeNull();
    expect(sessionStorage.getItem("sentinel_user")).toBeNull();
    expect(localStorage.getItem("sentinel_refresh_token")).toBeNull();
    expect(localStorage.getItem("sentinel_access_token")).toBeNull();
  });

  it("initialize restores state safely from sessionStorage", () => {
    const mockUser = {
      id: "u-session",
      email: "session@sentinelvoice.io",
      full_name: "Session Operator",
      is_active: true,
      is_verified: true,
      roles: ["USER" as const],
      created_at: "2026-11-13T10:00:00Z",
    };

    sessionStorage.setItem("sentinel_access_token", "session-access-jwt");
    sessionStorage.setItem("sentinel_user", JSON.stringify(mockUser));

    useAuthStore.getState().initialize();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe("session-access-jwt");
    expect(state.user?.email).toBe("session@sentinelvoice.io");
    expect(state.isLoading).toBe(false);
  });
});

