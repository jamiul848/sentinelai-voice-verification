import { apiClient } from "../client";
import { LoginPayload, RegisterPayload, TokenResponse, User } from "@/types";

export const authService = {
  /**
   * Register a new user account.
   * Maps to FastAPI POST /api/v1/auth/register.
   */
  async register(payload: RegisterPayload): Promise<{ user: User; message: string }> {
    const res = await apiClient.post("/api/v1/auth/register", payload);
    const data = res.data.data || res.data;
    return {
      user: data,
      message: res.data.message || "Registration successful. Please log in.",
    };
  },

  /**
   * Authenticate with email and password.
   * Maps to FastAPI POST /api/v1/auth/login.
   */
  async login(payload: LoginPayload): Promise<TokenResponse> {
    const res = await apiClient.post("/api/v1/auth/login", payload);
    const data = res.data.data || res.data;
    return data;
  },

  /**
   * Rotate access and refresh tokens.
   * Maps to FastAPI POST /api/v1/auth/refresh.
   * Backend accepts optional refresh_token in payload or reads HttpOnly sentinel_refresh_token cookie.
   */
  async refresh(refreshToken?: string): Promise<TokenResponse> {
    const payload = refreshToken ? { refresh_token: refreshToken } : {};
    const res = await apiClient.post("/api/v1/auth/refresh", payload);
    return res.data.data || res.data;
  },

  /**
   * Log out and invalidate active session.
   * Maps to FastAPI POST /api/v1/auth/logout.
   */
  async logout(): Promise<void> {
    try {
      const fallbackToken =
        typeof window !== "undefined"
          ? sessionStorage.getItem("sentinel_refresh_fallback") ||
            localStorage.getItem("sentinel_refresh_fallback")
          : undefined;
      const payload = fallbackToken ? { refresh_token: fallbackToken } : {};
      await apiClient.post("/api/v1/auth/logout", payload);
    } finally {
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("sentinel_access_token");
        sessionStorage.removeItem("sentinel_refresh_fallback");
        sessionStorage.removeItem("sentinel_user");
        localStorage.removeItem("sentinel_access_token");
        localStorage.removeItem("sentinel_refresh_token");
        localStorage.removeItem("sentinel_user");
      }
    }
  },
};
