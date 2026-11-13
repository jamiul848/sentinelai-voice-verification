import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { biometricsService } from "@/lib/api/services/biometrics.service";
import { consentService } from "@/lib/api/services/consent.service";
import { useDemoStore } from "@/store/useDemoStore";
import { DEMO_PROFILE, DEMO_VERIFICATION_HISTORY } from "@/config/demo";
import {
  ConsentStatusResponse,
  EnrollmentResponse,
  ReEnrollmentResponse,
  RevocationResponse,
  VerificationHistoryResponse,
  VerificationResponse,
  VoiceProfileDetailResponse,
} from "@/types";

export const BIOMETRICS_QUERY_KEYS = {
  profile: ["biometrics", "profile"] as const,
  profileHistory: ["biometrics", "profileHistory"] as const,
  verificationHistory: (params?: Record<string, unknown>) =>
    ["biometrics", "history", params] as const,
  consent: ["consent", "status"] as const,
};

/**
 * Hook to retrieve active voice biometric profile.
 */
export function useVoiceProfile() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<VoiceProfileDetailResponse | null>({
    queryKey: [...BIOMETRICS_QUERY_KEYS.profile, isDemoMode],
    queryFn: async () => {
      if (isDemoMode) {
        return {
          ...DEMO_PROFILE,
          enrollment_records: [
            {
              duration_sec: 3.4,
              rms_energy: 0.08,
              peak_amplitude: 0.65,
              audio_format: "WAV",
              snr_db: 24.1,
            },
          ],
        };
      }
      return await biometricsService.getProfile();
    },
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to retrieve verification history.
 */
export function useVerificationHistory(params?: {
  skip?: number;
  limit?: number;
  decision?: "MATCH" | "NO_MATCH";
  start_date?: string;
  end_date?: string;
  order?: "asc" | "desc";
}) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<VerificationHistoryResponse>({
    queryKey: [...BIOMETRICS_QUERY_KEYS.verificationHistory(params), isDemoMode],
    queryFn: async () => {
      if (isDemoMode) {
        let items = [...DEMO_VERIFICATION_HISTORY];
        if (params?.decision) {
          items = items.filter((h) => h.decision === params.decision);
        }
        return {
          total: items.length,
          skip: params?.skip ?? 0,
          limit: params?.limit ?? 50,
          items,
        };
      }
      return await biometricsService.getVerificationHistory(params);
    },
    staleTime: 15 * 1000,
  });
}

/**
 * Hook to check legal biometric consent status.
 */
export function useConsentStatus() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<ConsentStatusResponse>({
    queryKey: [...BIOMETRICS_QUERY_KEYS.consent, isDemoMode],
    queryFn: async () => {
      if (isDemoMode) {
        return { has_active_consent: true };
      }
      return await consentService.getStatus();
    },
    staleTime: 60 * 1000,
  });
}

/**
 * Mutation hook for voice enrollment.
 */
export function useEnrollVoice() {
  const queryClient = useQueryClient();
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useMutation<EnrollmentResponse, Error, { files: File[]; deviceInfo?: string }>({
    mutationFn: async ({ files, deviceInfo }) => {
      if (isDemoMode) {
        return {
          profile_id: "demo-profile-1",
          user_id: "demo-user-1",
          status: "ACTIVE",
          sample_count: files.length,
          mean_pairwise_similarity: 0.892,
          model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
          created_at: new Date().toISOString(),
          samples: [],
        };
      }
      return await biometricsService.enrollVoice(files, deviceInfo);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BIOMETRICS_QUERY_KEYS.profile });
      queryClient.invalidateQueries({ queryKey: ["biometrics", "history"] });
    },
  });
}

/**
 * Mutation hook for live voice verification.
 */
export function useVerifyVoice() {
  const queryClient = useQueryClient();
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useMutation<VerificationResponse, Error, { file: File }>({
    mutationFn: async ({ file }) => {
      if (isDemoMode) {
        return {
          verification_id: "demo-verif-" + Date.now(),
          decision: "MATCH",
          is_match: true,
          similarity_score: 0.884,
          applied_threshold: 0.405898,
          processing_time_ms: 320.5,
          model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
          threshold_version: "v1.0.0-eer-calibrated",
          timestamp: new Date().toISOString(),
        };
      }
      return await biometricsService.verifyVoice(file);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["biometrics", "history"] });
    },
  });
}

/**
 * Mutation hook for re-enrollment.
 */
export function useReEnrollVoice() {
  const queryClient = useQueryClient();
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useMutation<ReEnrollmentResponse, Error, { files: File[] }>({
    mutationFn: async ({ files }) => {
      if (isDemoMode) {
        return {
          profile_id: "demo-profile-new",
          previous_profile_id: "demo-profile-old",
          status: "ACTIVE",
          sample_count: files.length,
          mean_pairwise_similarity: 0.895,
          message: "Voiceprint re-enrollment successful (Demo Mode).",
        };
      }
      return await biometricsService.reEnrollVoice(files);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BIOMETRICS_QUERY_KEYS.profile });
      queryClient.invalidateQueries({ queryKey: ["biometrics", "history"] });
    },
  });
}

/**
 * Mutation hook for profile revocation.
 */
export function useRevokeVoiceProfile() {
  const queryClient = useQueryClient();
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useMutation<RevocationResponse, Error, void>({
    mutationFn: async () => {
      if (isDemoMode) {
        return {
          profile_id: "demo-profile-1",
          status: "REVOKED",
          message: "Demo profile marked as revoked.",
        };
      }
      return await biometricsService.revokeProfile();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: BIOMETRICS_QUERY_KEYS.profile });
      queryClient.invalidateQueries({ queryKey: ["biometrics", "history"] });
    },
  });
}
