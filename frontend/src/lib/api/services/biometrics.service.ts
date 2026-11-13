import { apiClient } from "../client";
import {
  EnrollmentResponse,
  ReEnrollmentResponse,
  RevocationResponse,
  VerificationHistoryResponse,
  VerificationResponse,
  VoiceProfile,
  VoiceProfileDetailResponse,
} from "@/types";

export const biometricsService = {
  /**
   * Submit 3 to 10 acoustic recordings for ECAPA-TDNN feature extraction and profile centroid aggregation.
   * Maps to FastAPI POST /api/v1/biometrics/enroll.
   */
  async enrollVoice(files: File[], deviceInfo?: string): Promise<EnrollmentResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });
    if (deviceInfo) {
      formData.append("device_info", deviceInfo);
    }

    const res = await apiClient.post("/api/v1/biometrics/enroll", formData, {
      timeout: 60000, // 60s timeout for neural embedding extraction
    });
    return res.data.data || res.data;
  },

  /**
   * Submit single acoustic probe recording for live 1:1 speaker verification evaluation.
   * Maps to FastAPI POST /api/v1/biometrics/verify.
   */
  async verifyVoice(file: File): Promise<VerificationResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await apiClient.post("/api/v1/biometrics/verify", formData, {
      timeout: 30000, // 30s timeout for model inference
    });
    return res.data.data || res.data;
  },

  /**
   * Retrieve active voiceprint profile and acoustic sample metadata.
   * Maps to FastAPI GET /api/v1/biometrics/profile.
   */
  async getProfile(): Promise<VoiceProfileDetailResponse | null> {
    try {
      const res = await apiClient.get("/api/v1/biometrics/profile");
      return res.data.data || res.data;
    } catch (err: any) {
      if (err.status === 404) {
        return null;
      }
      throw err;
    }
  },

  /**
   * Retrieve all historical voice profiles (ACTIVE and REVOKED).
   * Maps to FastAPI GET /api/v1/biometrics/profile/history.
   */
  async getProfileHistory(params?: {
    skip?: number;
    limit?: number;
  }): Promise<VoiceProfile[]> {
    const res = await apiClient.get("/api/v1/biometrics/profile/history", { params });
    return res.data.data || res.data;
  },

  /**
   * Re-enroll voiceprint: deactivates prior profile, shreds vector container, and enrolls new centroid.
   * Maps to FastAPI POST /api/v1/biometrics/profile/re-enroll.
   */
  async reEnrollVoice(files: File[]): Promise<ReEnrollmentResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const res = await apiClient.post("/api/v1/biometrics/profile/re-enroll", formData, {
      timeout: 60000,
    });
    return res.data.data || res.data;
  },

  /**
   * Permanently revoke voice profile with NIST SP 800-88 cryptographic shredding.
   * Maps to FastAPI DELETE /api/v1/biometrics/profile.
   */
  async revokeProfile(): Promise<RevocationResponse> {
    const res = await apiClient.delete("/api/v1/biometrics/profile");
    return res.data.data || res.data;
  },

  /**
   * Retrieve paginated history of verification evaluation attempts with filters.
   * Maps to FastAPI GET /api/v1/biometrics/verification-history.
   */
  async getVerificationHistory(params?: {
    skip?: number;
    limit?: number;
    decision?: "MATCH" | "NO_MATCH";
    start_date?: string;
    end_date?: string;
    order?: "asc" | "desc";
  }): Promise<VerificationHistoryResponse> {
    const res = await apiClient.get("/api/v1/biometrics/verification-history", { params });
    return res.data.data || res.data;
  },
};
