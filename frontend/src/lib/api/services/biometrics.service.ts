import { apiClient } from "../client";
import {
  EnrollmentResponse,
  RevocationResponse,
  VerificationHistoryResponse,
  VerificationResponse,
  VoiceProfile,
} from "@/types";

export const biometricsService = {
  /**
   * Submit 3+ acoustic recordings for ECAPA-TDNN feature extraction and profile aggregation.
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
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000, // 60s timeout for multi-sample deep learning inference
    });
    return res.data.data || res.data;
  },

  /**
   * Submit single acoustic probe recording for live 1:1 speaker verification evaluation.
   */
  async verifyVoice(file: File): Promise<VerificationResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await apiClient.post("/api/v1/biometrics/verify", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 30000,
    });
    return res.data.data || res.data;
  },

  /**
   * Retrieve active voiceprint profile metadata.
   */
  async getProfile(): Promise<VoiceProfile | null> {
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
   * Permanently revoke voice profile with NIST SP 800-88 cryptographic shredding.
   */
  async revokeProfile(): Promise<RevocationResponse> {
    const res = await apiClient.delete("/api/v1/biometrics/profile");
    return res.data.data || res.data;
  },

  /**
   * Retrieve paginated history of verification evaluation attempts.
   */
  async getVerificationHistory(params?: {
    skip?: number;
    limit?: number;
  }): Promise<VerificationHistoryResponse> {
    const res = await apiClient.get("/api/v1/biometrics/verification-history", { params });
    return res.data.data || res.data;
  },
};

