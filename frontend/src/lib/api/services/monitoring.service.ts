import { apiClient } from "../client";
import { HealthDetailedResponse, HealthLiveResponse, HealthReadyResponse } from "@/types";

export const monitoringService = {
  /**
   * Check lightweight service liveness probe.
   */
  async getLiveness(): Promise<HealthLiveResponse> {
    const res = await apiClient.get("/health/live");
    return res.data;
  },

  /**
   * Check system dependency readiness probe (PostgreSQL + Redis).
   */
  async getReadiness(): Promise<HealthReadyResponse> {
    const res = await apiClient.get("/health/ready");
    return res.data;
  },

  /**
   * Administrator: Check detailed engine, model cache, and security hardware status.
   */
  async getDetailedHealth(): Promise<HealthDetailedResponse> {
    const res = await apiClient.get("/health/detailed");
    return res.data;
  },
};

