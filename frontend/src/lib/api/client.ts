import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { ApiError } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Generate lightweight UUID for request correlation tracing (X-Request-ID).
 */
function generateRequestId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "req-" + Math.random().toString(36).substring(2, 15);
}

/**
 * Extract cookie value by name from document.cookie in browser context.
 */
function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^|;\\s*)(" + name + ")=([^;]*)"));
  return match ? decodeURIComponent(match[3]) : null;
}

/**
 * Core Axios client for Sentinel Voice API.
 * Standardized on credentials support (HttpOnly refresh cookies) and X-Request-ID tracing.
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30s timeout for model inference requests
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Attach Tracing, JWT Access Token & CSRF Protection
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 1. Attach Standardized X-Request-ID correlation header
    if (!config.headers["X-Request-ID"]) {
      config.headers["X-Request-ID"] = generateRequestId();
    }

    // 2. Attach JWT Access Token from sessionStorage or localStorage
    if (typeof window !== "undefined") {
      const token =
        sessionStorage.getItem("sentinel_access_token") ||
        localStorage.getItem("sentinel_access_token");
      if (token && !config.headers["Authorization"]) {
        config.headers["Authorization"] = `Bearer ${token}`;
      }

      // 3. Attach Double-Submit CSRF Token on state-mutating requests
      const method = config.method?.toUpperCase();
      if (method && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
        const csrfToken = getCookie("sentinel_csrf_token");
        if (csrfToken && !config.headers["X-CSRF-Token"]) {
          config.headers["X-CSRF-Token"] = csrfToken;
        }
      }

      // 4. For FormData (multipart uploads), delete default Content-Type so browser generates multipart boundary
      if (config.data instanceof FormData) {
        delete config.headers["Content-Type"];
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: 401 Silent Refresh & Unified Error Extraction
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized with token refresh rotation
    // Avoid re-invoking refresh on auth endpoints to prevent infinite refresh loops
    const isAuthRoute =
      originalRequest.url?.includes("/auth/login") ||
      originalRequest.url?.includes("/auth/register") ||
      originalRequest.url?.includes("/auth/refresh");

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthRoute) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers["Authorization"] = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Backend reads HttpOnly cookie sentinel_refresh_token when withCredentials: true.
        // Fallback to in-memory/sessionStorage token if present in payload.
        const fallbackRefreshToken =
          typeof window !== "undefined"
            ? sessionStorage.getItem("sentinel_refresh_fallback") ||
              localStorage.getItem("sentinel_refresh_fallback")
            : null;

        const refreshPayload = fallbackRefreshToken ? { refresh_token: fallbackRefreshToken } : {};

        const refreshRes = await axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          refreshPayload,
          {
            withCredentials: true,
            headers: {
              "Content-Type": "application/json",
              "X-Request-ID": generateRequestId(),
            },
          }
        );

        const newAccessToken =
          refreshRes.data.access_token ||
          refreshRes.data.data?.access_token;
        const newRefreshToken =
          refreshRes.data.refresh_token ||
          refreshRes.data.data?.refresh_token;

        if (typeof window !== "undefined") {
          sessionStorage.setItem("sentinel_access_token", newAccessToken);
          if (newRefreshToken) {
            sessionStorage.setItem("sentinel_refresh_fallback", newRefreshToken);
          }
        }

        processQueue(null, newAccessToken);
        originalRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        if (typeof window !== "undefined") {
          sessionStorage.removeItem("sentinel_access_token");
          sessionStorage.removeItem("sentinel_refresh_fallback");
          sessionStorage.removeItem("sentinel_user");
          localStorage.removeItem("sentinel_access_token");
          localStorage.removeItem("sentinel_user");
          window.dispatchEvent(new Event("sentinel:logout"));
        }
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    // Standardize error message extraction
    const errorData = error.response?.data;
    let extractedMessage = "An unexpected error occurred. Please try again.";

    if (errorData) {
      if (typeof errorData.detail === "string") {
        extractedMessage = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        extractedMessage = errorData.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
      } else if (errorData.message) {
        extractedMessage = errorData.message;
      }
    } else if (error.message) {
      extractedMessage = error.message;
    }

    const enhancedError = new Error(extractedMessage) as Error & {
      status?: number;
      retryAfter?: number;
      errorCode?: string;
    };
    enhancedError.status = error.response?.status;
    if (error.response?.headers && error.response.headers["retry-after"]) {
      enhancedError.retryAfter = parseInt(error.response.headers["retry-after"], 10);
    }

    return Promise.reject(enhancedError);
  }
);
