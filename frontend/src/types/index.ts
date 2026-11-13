/**
 * Sentinel Voice - Frontend TypeScript Type Definitions.
 * 
 * Accurately mirrors FastAPI Pydantic request models, response envelopes,
 * and database entities.
 */

// -----------------------------------------------------------------------------
// Unified API Response Envelope
// -----------------------------------------------------------------------------
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error_code?: string;
}

export interface ApiError {
  detail?: string | { loc: string[]; msg: string; type: string }[];
  message?: string;
  error_code?: string;
  retry_after?: number;
}

// -----------------------------------------------------------------------------
// Authentication & User Models
// -----------------------------------------------------------------------------
export type UserRole = "USER" | "ADMIN" | "SUPER_ADMIN" | "AUDITOR";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  roles: UserRole[];
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  csrf_token?: string;
  user: User;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  password: string;
  password_confirm: string;
  accept_privacy_terms: boolean;
}

export interface UpdateProfilePayload {
  full_name: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}

// -----------------------------------------------------------------------------
// Biometric Consent Models
// -----------------------------------------------------------------------------
export interface ConsentRecord {
  id: string;
  user_id: string;
  consent_type: string;
  consent_version: string;
  granted: boolean;
  created_at: string;
  revoked_at?: string | null;
  valid_until?: string | null;
}

export interface GrantConsentPayload {
  consent_version?: string;
  consent_type?: string;
}

export interface ConsentStatusResponse {
  has_active_consent: boolean;
  record?: ConsentRecord;
}

// -----------------------------------------------------------------------------
// Biometric Voice Models
// -----------------------------------------------------------------------------
export interface EnrollmentSampleMetadata {
  duration_sec: number;
  rms_energy: number;
  peak_amplitude: number;
  audio_format: string;
  snr_db?: number | null;
}

export interface EnrollmentResponse {
  profile_id: string;
  user_id: string;
  status: "ACTIVE" | "REVOKED";
  sample_count: number;
  mean_pairwise_similarity: number;
  model_identifier: string;
  created_at: string;
  samples: EnrollmentSampleMetadata[];
}

export interface VerificationResponse {
  verification_id: string;
  decision: "MATCH" | "NO_MATCH";
  is_match: boolean;
  similarity_score: number;
  applied_threshold: number;
  processing_time_ms: number;
  model_identifier: string;
  threshold_version?: string | null;
  threshold_id?: string | null;
  timestamp: string;
}

export interface VoiceProfile {
  id: string;
  user_id: string;
  status: "ACTIVE" | "REVOKED";
  sample_count: number;
  mean_pairwise_similarity: number;
  model_identifier: string;
  created_at: string;
  updated_at: string;
  revoked_at?: string | null;
}

export interface VoiceProfileDetailResponse extends VoiceProfile {
  enrollment_records: EnrollmentSampleMetadata[];
}

export interface ReEnrollmentResponse {
  profile_id: string;
  previous_profile_id?: string | null;
  status: "ACTIVE" | "REVOKED";
  sample_count: number;
  mean_pairwise_similarity: number;
  message: string;
}

export interface VerificationHistoryItem {
  id: string;
  decision: "MATCH" | "NO_MATCH";
  is_match: boolean;
  similarity_score: number;
  applied_threshold: number;
  processing_time_ms: number;
  created_at: string;
  threshold_id?: string | null;
  client_ip?: string | null;
}

export interface VerificationHistoryResponse {
  total: number;
  skip: number;
  limit: number;
  items: VerificationHistoryItem[];
}

export interface RevocationResponse {
  profile_id: string;
  status: string;
  message: string;
}

// -----------------------------------------------------------------------------
// Operational Health & Monitoring
// -----------------------------------------------------------------------------
export interface HealthLiveResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
}

export interface HealthReadyResponse {
  status: "ready" | "unready";
  service: string;
  version: string;
  components: {
    database: {
      status: "connected" | "disconnected";
      latency_ms?: number;
      error?: string;
    };
    redis: {
      status: "connected" | "disabled" | "unavailable";
      mode?: string;
      error?: string;
    };
  };
  timestamp: string;
}

export interface HealthDetailedResponse {
  status: string;
  service: string;
  version: string;
  uptime_seconds: number;
  components: {
    database: {
      status: string;
      latency_ms: number;
    };
    redis: {
      status: string;
    };
  };
  ecapa_engine: {
    model_identifier: string;
    device: string;
    loaded: boolean;
    embedding_dim: number;
  };
  biometric_storage: {
    storage_root: string;
    accessible: boolean;
  };
  encryption_service: {
    algorithm: string;
    configured: boolean;
  };
  timestamp: string;
}

// -----------------------------------------------------------------------------
// Administrator Fleet & Governance Models
// -----------------------------------------------------------------------------
export interface AdminUserListItem extends User {
  has_voice_profile?: boolean;
}

export interface ThresholdConfig {
  id: string;
  version_tag: string;
  model_identifier: string;
  calibrated_threshold: number;
  eer_percent: number;
  description: string;
  is_active: boolean;
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  user_id?: string | null;
  action: string;
  ip_address?: string | null;
  user_agent?: string | null;
  status: "SUCCESS" | "FAILURE" | "DENIED";
  details?: Record<string, any>;
  created_at: string;
}

