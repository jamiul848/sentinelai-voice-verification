import {
  AdminUserListItem,
  AuditLogEntry,
  ThresholdConfig,
  User,
  VerificationHistoryItem,
  VoiceProfile,
} from "@/types";

/**
 * Centrally isolated demo data for UI presentation and offline evaluation.
 * In accordance with Phase 8A rules:
 * - Kept strictly separate from production API handlers.
 * - Never used as silent fallback upon network errors.
 * - Always flagged with is_demo: true when presented.
 */

export const DEMO_USER: User = {
  id: "d3b07384-d113-4607-b353-832f01f8d48a",
  email: "sarah.connor@sentinelvoice.io",
  full_name: "Dr. Sarah Connor",
  is_active: true,
  is_verified: true,
  roles: ["USER", "ADMIN"],
  created_at: "2026-11-10T08:30:00Z",
};

export const DEMO_PROFILE: VoiceProfile = {
  id: "a1e8092f-7634-4bd2-976e-5a043818e901",
  user_id: "d3b07384-d113-4607-b353-832f01f8d48a",
  status: "ACTIVE",
  sample_count: 3,
  mean_pairwise_similarity: 0.8842,
  model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
  created_at: "2026-11-12T14:22:00Z",
  updated_at: "2026-11-12T14:22:00Z",
  revoked_at: null,
};

export const DEMO_VERIFICATION_HISTORY: VerificationHistoryItem[] = [
  {
    id: "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",
    decision: "MATCH",
    is_match: true,
    similarity_score: 0.8875,
    applied_threshold: 0.4059,
    processing_time_ms: 1240.5,
    created_at: "2026-11-13T08:46:07Z",
    threshold_id: "77a80b12-9c31-4e78-8380-49658ec3429a",
    client_ip: "127.0.0.1",
  },
  {
    id: "e377e6e5-0515-47ec-b23c-3aa3f8157985",
    decision: "NO_MATCH",
    is_match: false,
    similarity_score: 0.0707,
    applied_threshold: 0.4059,
    processing_time_ms: 1064.5,
    created_at: "2026-11-13T08:46:08Z",
    threshold_id: "77a80b12-9c31-4e78-8380-49658ec3429a",
    client_ip: "127.0.0.1",
  },
  {
    id: "c4b12984-2195-46f3-9978-0cb932148283",
    decision: "MATCH",
    is_match: true,
    similarity_score: 0.8124,
    applied_threshold: 0.4059,
    processing_time_ms: 1180.2,
    created_at: "2026-11-12T19:15:33Z",
    threshold_id: "77a80b12-9c31-4e78-8380-49658ec3429a",
    client_ip: "192.168.1.105",
  },
  {
    id: "9f8b72c1-8843-4351-9efb-419b48f932e1",
    decision: "MATCH",
    is_match: true,
    similarity_score: 0.7951,
    applied_threshold: 0.4059,
    processing_time_ms: 1310.8,
    created_at: "2026-11-11T11:02:14Z",
    threshold_id: "77a80b12-9c31-4e78-8380-49658ec3429a",
    client_ip: "192.168.1.105",
  },
];

export const DEMO_ADMIN_USERS: AdminUserListItem[] = [
  {
    id: "d3b07384-d113-4607-b353-832f01f8d48a",
    email: "sarah.connor@sentinelvoice.io",
    full_name: "Dr. Sarah Connor",
    is_active: true,
    is_verified: true,
    roles: ["USER", "ADMIN"],
    has_voice_profile: true,
    created_at: "2026-11-10T08:30:00Z",
  },
  {
    id: "8c7b6543-2190-44ec-9811-123456789abc",
    email: "john.reese@sentinelvoice.io",
    full_name: "John Reese",
    is_active: true,
    is_verified: true,
    roles: ["USER"],
    has_voice_profile: true,
    created_at: "2026-11-11T09:15:00Z",
  },
  {
    id: "7a6b5432-1089-43db-8700-098765432fed",
    email: "harold.finch@sentinelvoice.io",
    full_name: "Harold Finch",
    is_active: true,
    is_verified: true,
    roles: ["USER", "SUPER_ADMIN"],
    has_voice_profile: false,
    created_at: "2026-11-09T18:00:00Z",
  },
  {
    id: "6e5d4c3b-0978-42ca-76ff-a1b2c3d4e5f6",
    email: "root.cypher@sentinelvoice.io",
    full_name: "Root Samantha",
    is_active: false,
    is_verified: false,
    roles: ["USER"],
    has_voice_profile: false,
    created_at: "2026-11-12T12:00:00Z",
  },
];

export const DEMO_THRESHOLDS: ThresholdConfig[] = [
  {
    id: "77a80b12-9c31-4e78-8380-49658ec3429a",
    version_tag: "v1.0.0-eer-calibrated",
    model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
    calibrated_threshold: 0.405898,
    eer_percent: 1.25,
    description: "Equal Error Rate (EER) operating threshold calibrated on LibriSpeech clean trials.",
    is_active: true,
    created_at: "2026-11-13T01:00:00Z",
  },
  {
    id: "88b91c23-0d42-4f89-9491-5a769fd453ab",
    version_tag: "v0.9.0-high-security",
    model_identifier: "speechbrain/spkrec-ecapa-voxceleb",
    calibrated_threshold: 0.620000,
    eer_percent: 2.80,
    description: "High-security operating point minimizing False Acceptance Rate (FAR < 0.1%).",
    is_active: false,
    created_at: "2026-11-12T18:00:00Z",
  },
];

export const DEMO_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: "a1b2c3d4-e5f6-7890-1234-56789abcdef0",
    user_id: "d3b07384-d113-4607-b353-832f01f8d48a",
    action: "USER_AUTHENTICATION_SUCCESS",
    ip_address: "127.0.0.1",
    user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    status: "SUCCESS",
    created_at: "2026-11-13T09:00:00Z",
  },
  {
    id: "b2c3d4e5-f6a7-8901-2345-6789abcdef01",
    user_id: "d3b07384-d113-4607-b353-832f01f8d48a",
    action: "BIOMETRIC_VERIFICATION_EVALUATED",
    ip_address: "127.0.0.1",
    user_agent: "Mozilla/5.0",
    status: "SUCCESS",
    details: { decision: "MATCH", similarity: 0.8875 },
    created_at: "2026-11-13T08:46:07Z",
  },
  {
    id: "c3d4e5f6-a7b8-9012-3456-789abcdef012",
    user_id: "d3b07384-d113-4607-b353-832f01f8d48a",
    action: "CONSENT_RECORD_GRANTED",
    ip_address: "127.0.0.1",
    user_agent: "Mozilla/5.0",
    status: "SUCCESS",
    details: { consent_type: "VOICE_BIOMETRIC_ENROLLMENT", version: "1.0" },
    created_at: "2026-11-13T08:40:00Z",
  },
  {
    id: "d4e5f6a7-b8c9-0123-4567-89abcdef0123",
    user_id: null,
    action: "RATE_LIMIT_EXCEEDED",
    ip_address: "192.168.1.200",
    user_agent: "python-requests/2.31.0",
    status: "DENIED",
    details: { endpoint: "/api/v1/auth/login", retry_after_sec: 900 },
    created_at: "2026-11-13T07:15:00Z",
  },
];

export const DEMO_VERIFICATION_ACTIVITY_CHART = [
  { date: "Nov 07", matches: 12, nonMatches: 1 },
  { date: "Nov 08", matches: 19, nonMatches: 3 },
  { date: "Nov 09", matches: 15, nonMatches: 0 },
  { date: "Nov 10", matches: 28, nonMatches: 4 },
  { date: "Nov 11", matches: 34, nonMatches: 2 },
  { date: "Nov 12", matches: 42, nonMatches: 5 },
  { date: "Nov 13", matches: 51, nonMatches: 3 },
];

