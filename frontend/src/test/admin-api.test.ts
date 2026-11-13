import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminService } from "@/lib/api/services/admin.service";
import { userService } from "@/lib/api/services/user.service";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Phase 8D - Admin Service API Contracts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getOverview calls GET /api/v1/admin/overview", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        users: { total: 10, active: 8, inactive: 2 },
        voice_profiles: { total: 5, active: 4, revoked: 1 },
        verifications: { total: 100, matches: 80, no_matches: 20, match_rate: 80.0, avg_latency_ms: 125.5 },
      },
    });

    const data = await adminService.getOverview();
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/overview");
    expect(data.users.total).toBe(10);
    expect(data.verifications.matches).toBe(80);
  });

  it("getVoiceProfiles passes query parameters to GET /api/v1/admin/voice-profiles", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      },
    });

    await adminService.getVoiceProfiles({ limit: 20, skip: 10, status: "ACTIVE" });
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/voice-profiles", {
      params: {
        limit: 20,
        skip: 10,
        status: "ACTIVE",
      },
    });
  });

  it("revokeVoiceProfile posts to /api/v1/admin/voice-profiles/{id}/revoke", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        profile_id: "prof-1",
        status: "REVOKED",
        message: "Revoked",
      },
    });

    const res = await adminService.revokeVoiceProfile("prof-1");
    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/admin/voice-profiles/prof-1/revoke");
    expect(res.status).toBe("REVOKED");
  });

  it("getAnalytics requests analytics for specified days window", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        time_window_days: 14,
        total_verifications: 45,
        matches: 40,
        no_matches: 5,
        match_rate: 0.8889,
        avg_latency_ms: 110.0,
        timeline: [],
      },
    });

    const res = await adminService.getAnalytics(14);
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/analytics", {
      params: { days: 14 },
    });
    expect(res.total_verifications).toBe(45);
  });

  it("getThresholds calls GET /api/v1/admin/thresholds", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: [
        {
          id: "th-1",
          version_tag: "v1.0.0",
          threshold_value: 0.405898,
          is_active: true,
        },
      ],
    });

    const res = await adminService.getThresholds();
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/thresholds", { params: undefined });
    expect(res).toHaveLength(1);
    expect(res[0].threshold_value).toBe(0.405898);
  });

  it("createThreshold sends payload to POST /api/v1/admin/thresholds", async () => {
    const payload = {
      version_tag: "v2.0.0",
      threshold_value: 0.45,
      calibration_dataset: "LibriSpeech",
      optimization_criterion: "eer",
      model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
      eer_reported: 0.012,
    };

    (apiClient.post as any).mockResolvedValueOnce({
      data: { id: "th-2", ...payload, is_active: false },
    });

    const res = await adminService.createThreshold(payload);
    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/admin/thresholds", payload);
    expect(res.version_tag).toBe("v2.0.0");
  });

  it("activateThreshold posts to /api/v1/admin/thresholds/{id}/activate", async () => {
    (apiClient.post as any).mockResolvedValueOnce({
      data: { id: "th-2", is_active: true },
    });

    const res = await adminService.activateThreshold("th-2");
    expect(apiClient.post).toHaveBeenCalledWith("/api/v1/admin/thresholds/th-2/activate");
    expect(res.is_active).toBe(true);
  });

  it("getAuditLogs passes action and filter parameters", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: { items: [], total: 0, limit: 50, offset: 0 },
    });

    await adminService.getAuditLogs({ limit: 50, skip: 0, action: "AUTH" });
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/audit-logs", {
      params: { limit: 50, skip: 0, action: "AUTH" },
    });
  });

  it("getSecurityEvents calls GET /api/v1/admin/security-events", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        rate_limiter: { backend: "redis" },
        events: [],
      },
    });

    const res = await adminService.getSecurityEvents({ limit: 30 });
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/security-events", {
      params: { limit: 30 },
    });
    expect(res.rate_limiter.backend).toBe("redis");
  });

  it("getSystemHealthDetailed calls GET /health/detailed", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: { status: "healthy", components: {} },
    });

    const res = await adminService.getSystemHealthDetailed();
    expect(apiClient.get).toHaveBeenCalledWith("/health/detailed");
    expect(res.status).toBe("healthy");
  });

  it("userService getUserById and deleteUser invoke administrative endpoints", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: { id: "u-99", email: "test@domain.com" },
    });
    const user = await userService.getUserById("u-99");
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/admin/users/u-99");
    expect(user.id).toBe("u-99");

    (apiClient.delete as any).mockResolvedValueOnce({
      data: { deleted: true },
    });
    const del = await userService.deleteUser("u-99");
    expect(apiClient.delete).toHaveBeenCalledWith("/api/v1/admin/users/u-99");
    expect(del.deleted).toBe(true);
  });
});
