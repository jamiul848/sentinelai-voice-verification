import { create } from "zustand";
import { User } from "@/types";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User, accessToken: string, fallbackRefreshToken?: string) => void;
  setUser: (user: User) => void;
  clearAuth: () => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,

  setAuth: (user, accessToken, fallbackRefreshToken) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("sentinel_access_token", accessToken);
      sessionStorage.setItem("sentinel_user", JSON.stringify(user));
      if (fallbackRefreshToken) {
        sessionStorage.setItem("sentinel_refresh_fallback", fallbackRefreshToken);
      }
      // Clean up legacy localStorage tokens to ensure no persistent credentials linger
      localStorage.removeItem("sentinel_refresh_token");
      localStorage.removeItem("sentinel_access_token");
    }
    set({
      user,
      accessToken,
      isAuthenticated: true,
      isLoading: false,
    });
  },

  setUser: (user) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem("sentinel_user", JSON.stringify(user));
    }
    set({ user });
  },

  clearAuth: () => {
    if (typeof window !== "undefined") {
      sessionStorage.removeItem("sentinel_access_token");
      sessionStorage.removeItem("sentinel_refresh_fallback");
      sessionStorage.removeItem("sentinel_user");
      localStorage.removeItem("sentinel_refresh_token");
      localStorage.removeItem("sentinel_access_token");
      localStorage.removeItem("sentinel_user");
    }
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  initialize: () => {
    if (typeof window === "undefined") {
      set({ isLoading: false });
      return;
    }

    try {
      const token =
        sessionStorage.getItem("sentinel_access_token") ||
        localStorage.getItem("sentinel_access_token");
      const userStr =
        sessionStorage.getItem("sentinel_user") ||
        localStorage.getItem("sentinel_user");

      if (token && userStr) {
        const user = JSON.parse(userStr) as User;
        set({
          user,
          accessToken: token,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          isLoading: false,
        });
      }
    } catch {
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },
}));
