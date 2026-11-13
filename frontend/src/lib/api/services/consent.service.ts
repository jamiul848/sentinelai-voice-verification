import { apiClient } from "../client";
import { ConsentRecord, ConsentStatusResponse, GrantConsentPayload } from "@/types";

export const consentService = {
  /**
   * Check active consent status for currently authenticated user.
   */
  async getStatus(): Promise<ConsentStatusResponse> {
    try {
      const res = await apiClient.get("/api/v1/consent/me");
      const record = res.data.data || res.data;
      return {
        has_active_consent: !!record && record.granted === true,
        record: record,
      };
    } catch (err: any) {
      if (err.status === 404) {
        return { has_active_consent: false };
      }
      throw err;
    }
  },

  /**
   * Grant legal biometric processing authorization (GDPR / BIPA).
   */
  async grant(payload: GrantConsentPayload = {}): Promise<ConsentRecord> {
    const res = await apiClient.post("/api/v1/consent", {
      consent_type: payload.consent_type || "VOICE_BIOMETRIC_ENROLLMENT",
      consent_version: payload.consent_version || "1.0",
      granted: true,
    });
    return res.data.data || res.data;
  },

  /**
   * Revoke consent for voice biometric processing.
   */
  async revoke(): Promise<{ message: string }> {
    const res = await apiClient.delete("/api/v1/consent/me");
    return res.data;
  },
};

