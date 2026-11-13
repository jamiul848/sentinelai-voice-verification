import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminService } from "@/lib/api/services/admin.service";
import { monitoringService } from "@/lib/api/services/monitoring.service";
import { userService } from "@/lib/api/services/user.service";
import { useDemoStore } from "@/store/useDemoStore";
import {
  DEMO_ADMIN_USERS,
  DEMO_AUDIT_LOGS,
  DEMO_THRESHOLDS,
  DEMO_VERIFICATION_ACTIVITY_CHART,
} from "@/config/demo";
import {
  AdminAnalyticsResponse,
  AdminAuditLogListResponse,
  AdminOverviewResponse,
  AdminProfileListResponse,
  AdminSecurityEventsResponse,
  AdminUserListItem,
  HealthDetailedResponse,
  ThresholdConfigResponse,
  ThresholdCreatePayload,
  User,
} from "@/types";

export const ADMIN_QUERY_KEYS = {
  overview: ["admin", "overview"] as const,
  users: (params?: Record<string, unknown>) => ["admin", "users", params] as const,
  userDetail: (id: string) => ["admin", "user", id] as const,
  voiceProfiles: (params?: Record<string, unknown>) => ["admin", "voice-profiles", params] as const,
  analytics: (days?: number) => ["admin", "analytics", days] as const,
  thresholds: (params?: Record<string, unknown>) => ["admin", "thresholds", params] as const,
  activeThreshold: (model?: string) => ["admin", "thresholds", "active", model] as const,
  auditLogs: (params?: Record<string, unknown>) => ["admin", "audit-logs", params] as const,
  securityEvents: (params?: Record<string, unknown>) => ["admin", "security-events", params] as const,
  detailedHealth: ["admin", "system-health"] as const,
};

/**
 * Hook to retrieve platform overview statistics.
 */
export function useAdminOverview() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<AdminOverviewResponse>({
    queryKey: ADMIN_QUERY_KEYS.overview,
    queryFn: async () => {
      if (isDemoMode) {
        return {
          users: {
            total: DEMO_ADMIN_USERS.length,
            active: DEMO_ADMIN_USERS.filter((u) => u.is_active).length,
            inactive: DEMO_ADMIN_USERS.filter((u) => !u.is_active).length,
          },
          voice_profiles: {
            total: 12,
            active: 10,
            revoked: 2,
          },
          verifications: {
            total: 142,
            matches: 128,
            no_matches: 14,
            match_rate: 90.14,
            avg_latency_ms: 785.4,
          },
          system_health: {
            status: "ready",
            uptime_seconds: 18450.0,
            database_status: "connected",
            redis_status: "connected",
            model_loaded: true,
            encryption_configured: true,
          },
          recent_audit_events: [
            {
              id: "demo-aud-1",
              action: "VOICE_PROFILE_ENROLLED",
              resource_type: "voice_profile",
              resource_id: "demo-prof-1",
              created_at: new Date().toISOString(),
            },
            {
              id: "demo-aud-2",
              action: "USER_REGISTERED",
              resource_type: "user",
              resource_id: "demo-user-1",
              created_at: new Date(Date.now() - 3600000).toISOString(),
            },
          ],
        };
      }
      return await adminService.getOverview();
    },
    staleTime: 15_000,
  });
}

/**
 * Hook to list platform users with pagination and search.
 */
export function useAdminUsers(params?: { skip?: number; limit?: number; active_only?: boolean }) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<AdminUserListItem[]>({
    queryKey: ADMIN_QUERY_KEYS.users(params),
    queryFn: async () => {
      if (isDemoMode) {
        let list = [...DEMO_ADMIN_USERS];
        if (params?.active_only) {
          list = list.filter((u) => u.is_active);
        }
        return list;
      }
      return await userService.getUsers(params);
    },
    staleTime: 30_000,
  });
}

/**
 * Hook to retrieve user details by ID.
 */
export function useAdminUserDetails(userId: string) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<User>({
    queryKey: ADMIN_QUERY_KEYS.userDetail(userId),
    queryFn: async () => {
      if (isDemoMode) {
        const found = DEMO_ADMIN_USERS.find((u) => u.id === userId);
        if (!found) throw new Error("User not found");
        return found;
      }
      return await userService.getUserById(userId);
    },
    enabled: Boolean(userId),
  });
}

/**
 * Mutation to toggle user active status.
 */
export function useUpdateUserStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ userId, isActive }: { userId: string; isActive: boolean }) => {
      return await userService.updateUserStatus(userId, isActive);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.overview });
    },
  });
}

/**
 * Mutation to update user roles.
 */
export function useUpdateUserRoles() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ userId, roles }: { userId: string; roles: string[] }) => {
      return await userService.updateUserRoles(userId, roles);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.overview });
    },
  });
}

/**
 * Mutation to delete user account.
 */
export function useDeleteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId: string) => {
      return await userService.deleteUser(userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.overview });
    },
  });
}

/**
 * Hook to list voice profiles across all accounts.
 */
export function useAdminVoiceProfiles(params?: {
  skip?: number;
  limit?: number;
  status?: string;
  user_id?: string;
}) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<AdminProfileListResponse>({
    queryKey: ADMIN_QUERY_KEYS.voiceProfiles(params),
    queryFn: async () => {
      if (isDemoMode) {
        return {
          total: 2,
          items: [
            {
              id: "demo-prof-uuid-1",
              user_id: "demo-user-1",
              user_email: "operator@sentinelvoice.io",
              user_full_name: "Sarah Connor",
              status: "ACTIVE",
              sample_count: 3,
              mean_pairwise_similarity: 0.8872,
              model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
              created_at: new Date(Date.now() - 86400000).toISOString(),
              updated_at: new Date(Date.now() - 86400000).toISOString(),
            },
            {
              id: "demo-prof-uuid-2",
              user_id: "demo-user-2",
              user_email: "auditor@sentinelvoice.io",
              user_full_name: "John Connor",
              status: "REVOKED",
              sample_count: 3,
              mean_pairwise_similarity: 0.8521,
              model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
              created_at: new Date(Date.now() - 172800000).toISOString(),
              updated_at: new Date(Date.now() - 86400000).toISOString(),
              revoked_at: new Date(Date.now() - 86400000).toISOString(),
            },
          ],
        };
      }
      return await adminService.getVoiceProfiles(params);
    },
    staleTime: 30_000,
  });
}

/**
 * Mutation to revoke a voice profile administratively.
 */
export function useRevokeVoiceProfileAdmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (profileId: string) => {
      return await adminService.revokeVoiceProfile(profileId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "voice-profiles"] });
      queryClient.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.overview });
    },
  });
}

/**
 * Hook to retrieve verification analytics.
 */
export function useAdminAnalytics(days: number = 7) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<AdminAnalyticsResponse>({
    queryKey: ADMIN_QUERY_KEYS.analytics(days),
    queryFn: async () => {
      if (isDemoMode) {
        return {
          total_verifications: 142,
          matches: 128,
          no_matches: 14,
          match_rate: 90.14,
          no_match_rate: 9.86,
          average_latency_ms: 785.4,
          timeline: DEMO_VERIFICATION_ACTIVITY_CHART.map((c) => ({
            date: c.date,
            matches: c.matches,
            no_matches: c.nonMatches,
            total: c.matches + c.nonMatches,
            avg_latency_ms: 790.0,
          })),
          active_threshold: {
            version_tag: "librispeech-dev-clean-eer-v1.0",
            model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
            threshold_value: 0.405898,
            calibration_dataset: "LibriSpeech dev-clean",
            calibration_criterion: "EER Minimization",
          },
        };
      }
      return await adminService.getAnalytics(days);
    },
    staleTime: 30_000,
  });
}

/**
 * Hook to list threshold configurations.
 */
export function useAdminThresholds(params?: { skip?: number; limit?: number }) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<ThresholdConfigResponse[]>({
    queryKey: ADMIN_QUERY_KEYS.thresholds(params),
    queryFn: async () => {
      if (isDemoMode) {
        return DEMO_THRESHOLDS.map((t) => ({
          id: t.id,
          version_tag: t.version_tag,
          model_identifier: t.model_identifier,
          threshold_value: t.calibrated_threshold,
          calibration_dataset: "LibriSpeech dev-clean",
          calibration_criterion: "equal_error_rate_minimization",
          calibration_metadata: { eer: t.eer_percent / 100 },
          is_active: t.is_active,
          created_at: t.created_at,
          updated_at: t.created_at,
        }));
      }
      return await adminService.getThresholds(params);
    },
    staleTime: 60_000,
  });
}

/**
 * Hook to get the active threshold.
 */
export function useActiveThreshold(modelIdentifier?: string) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<ThresholdConfigResponse | null>({
    queryKey: ADMIN_QUERY_KEYS.activeThreshold(modelIdentifier),
    queryFn: async () => {
      if (isDemoMode) {
        const active = DEMO_THRESHOLDS.find((t) => t.is_active);
        if (!active) return null;
        return {
          id: active.id,
          version_tag: active.version_tag,
          model_identifier: active.model_identifier,
          threshold_value: active.calibrated_threshold,
          calibration_dataset: "LibriSpeech dev-clean",
          calibration_criterion: "equal_error_rate_minimization",
          calibration_metadata: { eer: active.eer_percent / 100 },
          is_active: true,
          created_at: active.created_at,
          updated_at: active.created_at,
        };
      }
      return await adminService.getActiveThreshold(modelIdentifier);
    },
    staleTime: 60_000,
  });
}

/**
 * Mutation to create a new threshold configuration.
 */
export function useCreateThreshold() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ThresholdCreatePayload) => {
      return await adminService.createThreshold(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "thresholds"] });
    },
  });
}

/**
 * Mutation to activate a threshold configuration.
 */
export function useActivateThreshold() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (thresholdId: string) => {
      return await adminService.activateThreshold(thresholdId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "thresholds"] });
      queryClient.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.overview });
    },
  });
}

/**
 * Hook to query global audit logs.
 */
export function useAdminAuditLogs(params?: {
  skip?: number;
  limit?: number;
  action?: string;
  resource_type?: string;
  actor_user_id?: string;
}) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<AdminAuditLogListResponse>({
    queryKey: ADMIN_QUERY_KEYS.auditLogs(params),
    queryFn: async () => {
      if (isDemoMode) {
        return {
          total: DEMO_AUDIT_LOGS.length,
          skip: params?.skip || 0,
          limit: params?.limit || 50,
          items: DEMO_AUDIT_LOGS.map((log) => ({
            id: log.id,
            actor_user_id: log.user_id,
            actor_email: "operator@sentinelvoice.io",
            action: log.action,
            resource_type: "system",
            resource_id: log.id,
            changes: log.details || null,
            created_at: log.created_at,
          })),
        };
      }
      return await adminService.getAuditLogs(params);
    },
    staleTime: 15_000,
  });
}

/**
 * Hook to query security incidents and rate-limiting status.
 */
export function useAdminSecurityEvents(params?: { skip?: number; limit?: number }) {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<AdminSecurityEventsResponse>({
    queryKey: ADMIN_QUERY_KEYS.securityEvents(params),
    queryFn: async () => {
      if (isDemoMode) {
        return {
          total: 3,
          events: [
            {
              id: "sec-ev-1",
              actor_user_id: "demo-user-1",
              actor_email: "admin@sentinelvoice.io",
              action: "USER_DEACTIVATED",
              resource_type: "user",
              resource_id: "target-user-2",
              changes: { is_active: false },
              created_at: new Date(Date.now() - 7200000).toISOString(),
            },
            {
              id: "sec-ev-2",
              actor_user_id: "demo-user-1",
              actor_email: "admin@sentinelvoice.io",
              action: "THRESHOLD_ACTIVATED",
              resource_type: "threshold_configuration",
              resource_id: "thresh-1",
              changes: { version_tag: "v1.0" },
              created_at: new Date(Date.now() - 14400000).toISOString(),
            },
          ],
          rate_limiter: {
            backend: "in-memory (sliding-window)",
            rules: {
              auth_login: "5/min",
              auth_register: "3/hour",
              biometrics_verify: "10/min",
              biometrics_enroll: "5/hour",
            },
            redis_configured: false,
          },
        };
      }
      return await adminService.getSecurityEvents(params);
    },
    staleTime: 15_000,
  });
}

/**
 * Hook to query detailed operational health.
 */
export function useSystemHealthDetailed() {
  const isDemoMode = useDemoStore((s) => s.isDemoMode);

  return useQuery<HealthDetailedResponse>({
    queryKey: ADMIN_QUERY_KEYS.detailedHealth,
    queryFn: async () => {
      if (isDemoMode) {
        return {
          status: "ready",
          service: "Sentinel Voice Platform",
          version: "0.1.0",
          uptime_seconds: 18450,
          components: {
            database: { status: "connected", latency_ms: 0.47 },
            redis: { status: "connected" },
          },
          ecapa_engine: {
            model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
            device: "cpu",
            loaded: true,
            embedding_dim: 192,
          },
          biometric_storage: {
            storage_root: "biometric_store",
            accessible: true,
          },
          encryption_service: {
            algorithm: "AES-256-GCM-Envelope-V2",
            configured: true,
          },
          timestamp: new Date().toISOString(),
        };
      }
      return await monitoringService.getDetailedHealth();
    },
    staleTime: 10_000,
  });
}
