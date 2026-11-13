import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { ApiError } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

/**
 * Generate lightweight UUID for request correlation tracing.
 */
function generateCorrelationId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "req-" + Math.random().toString(36).substring(2, 15);
}

/**
 * Core Axios client for Sentinel Voice API.
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30s timeout for model inference requests
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor: Attach Auth & Tracing
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 1. Attach Request Correlation ID
    if (!config.headers["X-Correlation-ID"]) {
      config.headers["X-Correlation-ID"] = generateCorrelationId();
    }

    // 2. Attach JWT Access Token from local storage / cookie
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("sentinel_access_token");
      if (token && !config.headers["Authorization"]) {
        config.headers["Authorization"] = `Bearer ${token}`;
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
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes("/auth/")) {
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
        const refreshToken = typeof window !== "undefined" ? localStorage.getItem("sentinel_refresh_token") : null;
        if (!refreshToken) {
          throw new Error("No refresh token available");
        }

        const refreshRes = await axios.post(
          `${API_BASE_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken },
          { headers: { "Content-Type": "application/json" } }
        );

        const newAccessToken = refreshRes.data.access_token || refreshRes.data.data?.access_token;
        const newRefreshToken = refreshRes.data.refresh_token || refreshRes.data.data?.refresh_token;

        if (typeof window !== "undefined") {
          localStorage.setItem("sentinel_access_token", newAccessToken);
          if (newRefreshToken) {
            localStorage.setItem("sentinel_refresh_token", newRefreshToken);
          }
        }

        processQueue(null, newAccessToken);
        originalRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        if (typeof window !== "undefined") {
          localStorage.removeItem("sentinel_access_token");
          localStorage.removeItem("sentinel_refresh_token");
          localStorage.removeItem("sentinel_user");
          // Optionally trigger logout event
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
        extractedMessage = errorData.detail.map((d: any) => d.msg).join(", ");
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

