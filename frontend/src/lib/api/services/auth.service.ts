import { apiClient } from "../client";
import { LoginPayload, RegisterPayload, TokenResponse, User } from "@/types";

export const authService = {
  /**
   * Register a new user account.
   */
  async register(payload: RegisterPayload): Promise<{ user: User; message: string }> {
    const res = await apiClient.post("/api/v1/auth/register", payload);
    // API returns ApiResponse[UserResponse] or UserResponse directly
    const data = res.data.data || res.data;
    return {
      user: data,
      message: res.data.message || "Registration successful. Please log in.",
    };
  },

  /**
   * Authenticate with email and password.
   */
  async login(payload: LoginPayload): Promise<TokenResponse> {
    const res = await apiClient.post("/api/v1/auth/login", payload);
    const data = res.data.data || res.data;
    return data;
  },

  /**
   * Rotate access and refresh tokens.
   */
  async refresh(refreshToken: string): Promise<TokenResponse> {
    const res = await apiClient.post("/api/v1/auth/refresh", { refresh_token: refreshToken });
    return res.data.data || res.data;
  },

  /**
   * Log out and invalidate active session.
   */
  async logout(): Promise<void> {
    try {
      await apiClient.post("/api/v1/auth/logout");
    } finally {
      if (typeof window !== "undefined") {
        localStorage.removeItem("sentinel_access_token");
        localStorage.removeItem("sentinel_refresh_token");
        localStorage.removeItem("sentinel_user");
      }
    }
  },
};

