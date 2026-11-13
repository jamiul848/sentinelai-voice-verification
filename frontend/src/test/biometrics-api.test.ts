import { beforeEach, describe, expect, it, vi } from "vitest";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { apiClient } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe("Phase 8C - Biometrics Service API Contracts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("enrollVoice builds FormData with 'files' plural key and posts to /api/v1/biometrics/enroll", async () => {
    const mockFiles = [
      new File(["sample1"], "utterance1.wav", { type: "audio/wav" }),
      new File(["sample2"], "utterance2.wav", { type: "audio/wav" }),
      new File(["sample3"], "utterance3.wav", { type: "audio/wav" }),
    ];

    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        profile_id: "prof-123",
        status: "ACTIVE",
        sample_count: 3,
        mean_pairwise_similarity: 0.89,
      },
    });

    const res = await biometricsService.enrollVoice(mockFiles, "Test Device");

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    const [endpoint, formData, config] = (apiClient.post as any).mock.calls[0];

    expect(endpoint).toBe("/api/v1/biometrics/enroll");
    expect(formData instanceof FormData).toBe(true);
    expect(formData.getAll("files")).toHaveLength(3);
    expect(formData.get("device_info")).toBe("Test Device");
    expect(config.timeout).toBe(60000);
    expect(res.profile_id).toBe("prof-123");
  });

  it("verifyVoice builds FormData with 'file' singular key and posts to /api/v1/biometrics/verify", async () => {
    const mockProbe = new File(["probe-bytes"], "probe.wav", { type: "audio/wav" });

    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        verification_id: "verif-456",
        decision: "MATCH",
        is_match: true,
        similarity_score: 0.842,
        applied_threshold: 0.405898,
        processing_time_ms: 250,
      },
    });

    const res = await biometricsService.verifyVoice(mockProbe);

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    const [endpoint, formData, config] = (apiClient.post as any).mock.calls[0];

    expect(endpoint).toBe("/api/v1/biometrics/verify");
    expect(formData instanceof FormData).toBe(true);
    expect(formData.get("file")).toBeTruthy();
    expect(config.timeout).toBe(30000);
    expect(res.decision).toBe("MATCH");
    expect(res.is_match).toBe(true);
  });

  it("getProfile queries GET /api/v1/biometrics/profile and returns null on 404", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        id: "prof-1",
        status: "ACTIVE",
        sample_count: 3,
      },
    });

    const profile = await biometricsService.getProfile();
    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/biometrics/profile");
    expect(profile?.id).toBe("prof-1");

    // Test 404 handling
    (apiClient.get as any).mockRejectedValueOnce({ status: 404 });
    const nullProfile = await biometricsService.getProfile();
    expect(nullProfile).toBeNull();
  });

  it("reEnrollVoice posts to /api/v1/biometrics/profile/re-enroll with 'files' key", async () => {
    const newFiles = [
      new File(["s1"], "s1.wav", { type: "audio/wav" }),
      new File(["s2"], "s2.wav", { type: "audio/wav" }),
      new File(["s3"], "s3.wav", { type: "audio/wav" }),
    ];

    (apiClient.post as any).mockResolvedValueOnce({
      data: {
        profile_id: "new-prof",
        previous_profile_id: "old-prof",
        status: "ACTIVE",
        sample_count: 3,
        message: "Voiceprint re-enrollment successful.",
      },
    });

    const res = await biometricsService.reEnrollVoice(newFiles);

    expect(apiClient.post).toHaveBeenCalledWith(
      "/api/v1/biometrics/profile/re-enroll",
      expect.any(FormData),
      expect.objectContaining({ timeout: 60000 })
    );
    expect(res.profile_id).toBe("new-prof");
    expect(res.previous_profile_id).toBe("old-prof");
  });

  it("revokeProfile calls DELETE /api/v1/biometrics/profile", async () => {
    (apiClient.delete as any).mockResolvedValueOnce({
      data: {
        profile_id: "prof-to-revoke",
        status: "REVOKED",
        message: "Voice profile revoked and biometric vector shredded.",
      },
    });

    const res = await biometricsService.revokeProfile();

    expect(apiClient.delete).toHaveBeenCalledWith("/api/v1/biometrics/profile");
    expect(res.status).toBe("REVOKED");
  });

  it("getVerificationHistory queries GET /api/v1/biometrics/verification-history with pagination and decision filters", async () => {
    (apiClient.get as any).mockResolvedValueOnce({
      data: {
        total: 10,
        skip: 0,
        limit: 25,
        items: [],
      },
    });

    await biometricsService.getVerificationHistory({
      skip: 0,
      limit: 25,
      decision: "MATCH",
      order: "desc",
    });

    expect(apiClient.get).toHaveBeenCalledWith("/api/v1/biometrics/verification-history", {
      params: {
        skip: 0,
        limit: 25,
        decision: "MATCH",
        order: "desc",
      },
    });
  });
});

