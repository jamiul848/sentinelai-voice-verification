import { apiClient } from "../client";
import { ConsentRecord, ConsentStatusResponse, GrantConsentPayload } from "@/types";

export const consentService = {
  /**
   * Check active consent status for currently authenticated user.
   * Maps to FastAPI GET /api/v1/consent/me.
   */
  async getStatus(): Promise<ConsentStatusResponse> {
    try {
      const res = await apiClient.get("/api/v1/consent/me");
      const data = res.data.data || res.data;
      return {
        has_active_consent: !!data.has_active_consent,
        record: data.current_consent || data.record,
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
   * Maps to FastAPI POST /api/v1/consent.
   */
  async grant(payload: GrantConsentPayload = {}): Promise<ConsentRecord> {
    const res = await apiClient.post("/api/v1/consent", {
      consent_type: payload.consent_type || "VOICE_BIOMETRIC_ENROLLMENT",
      consent_version: payload.consent_version || "1.0",
    });
    return res.data.data || res.data;
  },

  /**
   * Revoke consent for voice biometric processing.
   * Maps to FastAPI POST /api/v1/consent/revoke.
   */
  async revoke(reason?: string): Promise<{ message: string }> {
    const res = await apiClient.post("/api/v1/consent/revoke", {
      consent_type: "VOICE_BIOMETRIC_ENROLLMENT",
      reason: reason || "User requested consent revocation",
    });
    return {
      message: res.data.message || "Consent revoked successfully.",
    };
  },
};
