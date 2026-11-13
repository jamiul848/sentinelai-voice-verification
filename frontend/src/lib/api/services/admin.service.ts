import { apiClient } from "../client";
import {
  AdminAnalyticsResponse,
  AdminAuditLogListResponse,
  AdminOverviewResponse,
  AdminProfileListResponse,
  AdminSecurityEventsResponse,
  ThresholdConfigResponse,
  ThresholdCreatePayload,
} from "@/types";

export const adminService = {
  /**
   * Fetch platform-wide statistics, active counts, and system summary.
   * Maps to FastAPI GET /api/v1/admin/overview.
   */
  async getOverview(): Promise<AdminOverviewResponse> {
    const res = await apiClient.get("/api/v1/admin/overview");
    return res.data.data || res.data;
  },

  /**
   * Fetch all voice profiles across all accounts.
   * Maps to FastAPI GET /api/v1/admin/voice-profiles.
   */
  async getVoiceProfiles(params?: {
    skip?: number;
    limit?: number;
    status?: string;
    user_id?: string;
  }): Promise<AdminProfileListResponse> {
    const res = await apiClient.get("/api/v1/admin/voice-profiles", { params });
    return res.data.data || res.data;
  },

  /**
   * Admin revocation and cryptographic vector shredding.
   * Maps to FastAPI POST /api/v1/admin/voice-profiles/{profileId}/revoke.
   */
  async revokeVoiceProfile(profileId: string): Promise<{
    profile_id: string;
    status: string;
    message: string;
  }> {
    const res = await apiClient.post(`/api/v1/admin/voice-profiles/${profileId}/revoke`);
    return res.data.data || res.data;
  },

  /**
   * Verification analytics, match/no-match distributions, and processing latencies.
   * Maps to FastAPI GET /api/v1/admin/analytics.
   */
  async getAnalytics(days: number = 7): Promise<AdminAnalyticsResponse> {
    const res = await apiClient.get("/api/v1/admin/analytics", { params: { days } });
    return res.data.data || res.data;
  },

  /**
   * List all registered threshold configurations with provenance.
   * Maps to FastAPI GET /api/v1/admin/thresholds.
   */
  async getThresholds(params?: { skip?: number; limit?: number }): Promise<ThresholdConfigResponse[]> {
    const res = await apiClient.get("/api/v1/admin/thresholds", { params });
    return res.data.data || res.data;
  },

  /**
   * Get currently active decision threshold for a model.
   * Maps to FastAPI GET /api/v1/admin/thresholds/active.
   */
  async getActiveThreshold(modelIdentifier?: string): Promise<ThresholdConfigResponse | null> {
    const res = await apiClient.get("/api/v1/admin/thresholds/active", {
      params: { model_identifier: modelIdentifier },
    });
    return res.data.data || res.data;
  },

  /**
   * Register a new calibrated threshold configuration.
   * Maps to FastAPI POST /api/v1/admin/thresholds.
   */
  async createThreshold(payload: ThresholdCreatePayload): Promise<ThresholdConfigResponse> {
    const res = await apiClient.post("/api/v1/admin/thresholds", payload);
    return res.data.data || res.data;
  },

  /**
   * Activate an operational decision threshold.
   * Maps to FastAPI POST /api/v1/admin/thresholds/{thresholdId}/activate.
   */
  async activateThreshold(thresholdId: string): Promise<ThresholdConfigResponse> {
    const res = await apiClient.post(`/api/v1/admin/thresholds/${thresholdId}/activate`);
    return res.data.data || res.data;
  },

  /**
   * Query global immutable audit logs with filters.
   * Maps to FastAPI GET /api/v1/admin/audit-logs.
   */
  async getAuditLogs(params?: {
    skip?: number;
    limit?: number;
    action?: string;
    resource_type?: string;
    actor_user_id?: string;
  }): Promise<AdminAuditLogListResponse> {
    const res = await apiClient.get("/api/v1/admin/audit-logs", { params });
    return res.data.data || res.data;
  },

  /**
   * Query security incidents and rate limiter status.
   * Maps to FastAPI GET /api/v1/admin/security-events.
   */
  async getSecurityEvents(params?: {
    skip?: number;
    limit?: number;
  }): Promise<AdminSecurityEventsResponse> {
    const res = await apiClient.get("/api/v1/admin/security-events", { params });
    return res.data.data || res.data;
  },

  /**
   * Query detailed diagnostic health probes.
   * Maps to FastAPI GET /health/detailed.
   */
  async getSystemHealthDetailed(): Promise<any> {
    const res = await apiClient.get("/health/detailed");
    return res.data.data || res.data;
  },
};
