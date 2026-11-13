# SENTINEL VOICE – PHASE 8D API CONTRACT SPECIFICATION
## Administrator Console & System Monitoring API Architecture

This document establishes the definitive REST API contracts, parameter mappings, role-based authorization requirements, and security invariants for the Sentinel Voice Administrator Console (Phase 8D).

---

### 1. Security & RBAC Principles
- **Authoritative Server Guards:** Frontend route guards (`RouteGuard`) are UX conveniences only. Every single administrative HTTP request is validated authoritatively by FastAPI dependency `require_admin = require_role("ADMIN", "SUPER_ADMIN")`.
- **Zero Vector & Secret Exposure:** Biometric embeddings, raw audio recordings, encryption keys, and internal filesystem paths are NEVER exposed in any administrative API response.
- **Auditability:** All state-changing administrative operations (status toggles, role assignments, user deletions, profile revocations, threshold activations) append immutable records to `audit_logs`.

---

### 2. Administrator Endpoints Specification

#### A. Platform Overview & System Statistics
- **Route:** `GET /api/v1/admin/overview`
- **Authorization:** `Bearer <token>` (ADMIN or SUPER_ADMIN)
- **Response Schema:** `ApiResponse[AdminOverviewResponse]`
```json
{
  "success": true,
  "message": "Platform overview retrieved successfully.",
  "data": {
    "users": {
      "total": 15,
      "active": 14,
      "inactive": 1
    },
    "voice_profiles": {
      "total": 12,
      "active": 10,
      "revoked": 2
    },
    "verifications": {
      "total": 45,
      "matches": 38,
      "no_matches": 7,
      "match_rate": 84.44,
      "avg_latency_ms": 820.5
    },
    "system_health": {
      "status": "ready",
      "uptime_seconds": 12450.2,
      "database_status": "connected",
      "redis_status": "disabled",
      "model_loaded": false,
      "encryption_configured": true
    },
    "recent_audit_events": [
      {
        "id": "uuid",
        "action": "VOICE_PROFILE_ENROLLED",
        "resource_type": "voice_profile",
        "resource_id": "prof-uuid",
        "actor_user_id": "user-uuid",
        "created_at": "2026-11-13T12:00:00Z"
      }
    ]
  }
}
```

---

#### B. User Management (Existing & Extended)
- **List Users:** `GET /api/v1/admin/users?skip=0&limit=50&active_only=false`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Response: `ApiResponse[List[UserResponse]]`
- **Get User By ID:** `GET /api/v1/admin/users/{user_id}`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Response: `ApiResponse[UserResponse]`
- **Update User Active Status:** `PATCH /api/v1/admin/users/{user_id}/status`
  - Payload: `{"is_active": boolean}`
  - Invariants: Cannot deactivate self; cannot deactivate last administrator.
  - Response: `ApiResponse[UserResponse]`
- **Update User Roles:** `PATCH /api/v1/admin/users/{user_id}/roles`
  - Payload: `{"roles": ["USER", "ADMIN"]}`
  - Invariants: Cannot remove ADMIN from last administrator.
  - Response: `ApiResponse[UserResponse]`
- **Delete User Account:** `DELETE /api/v1/admin/users/{user_id}`
  - Invariants: Cannot delete self; cannot delete last administrator.
  - Response: `ApiResponse[dict]`

---

#### C. Biometric Voice Profiles Management
- **List All Voice Profiles:** `GET /api/v1/admin/voice-profiles?skip=0&limit=50&status=ACTIVE`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Parameters:
    - `skip` (int, default 0)
    - `limit` (int, default 50, max 200)
    - `status` (optional str: `ACTIVE` or `REVOKED`)
    - `user_id` (optional UUID)
  - Response Schema: `ApiResponse[AdminProfileListResponse]`
```json
{
  "success": true,
  "message": "Retrieved 10 voice profiles.",
  "data": {
    "total": 10,
    "items": [
      {
        "id": "prof-uuid",
        "user_id": "user-uuid",
        "user_email": "operator@sentinelvoice.io",
        "user_full_name": "Sarah Connor",
        "status": "ACTIVE",
        "sample_count": 3,
        "mean_pairwise_similarity": 0.8872,
        "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
        "created_at": "2026-11-13T10:00:00Z",
        "updated_at": "2026-11-13T10:00:00Z",
        "revoked_at": null
      }
    ]
  }
}
```
- **Admin Revocation & Vector Shredding:** `POST /api/v1/admin/voice-profiles/{profile_id}/revoke`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Effects: Invokes `BiometricStorageManager.shred_vector_file()`, marks status `REVOKED`, logs audit event.
  - Response Schema: `ApiResponse[ProfileRevocationResponse]`

---

#### D. Verification Analytics
- **Route:** `GET /api/v1/admin/analytics?days=7`
- **Authorization:** `ADMIN`, `SUPER_ADMIN`
- **Parameters:** `days` (int, 1-90, default 7)
- **Response Schema:** `ApiResponse[AdminAnalyticsResponse]`
```json
{
  "success": true,
  "message": "Verification analytics calculated.",
  "data": {
    "total_verifications": 142,
    "matches": 128,
    "no_matches": 14,
    "match_rate": 90.14,
    "no_match_rate": 9.86,
    "average_latency_ms": 785.4,
    "timeline": [
      {
        "date": "2026-11-13",
        "matches": 24,
        "no_matches": 2,
        "total": 26,
        "avg_latency_ms": 810.2
      }
    ],
    "active_threshold": {
      "version_tag": "librispeech-dev-clean-eer-v1.0",
      "threshold_value": 0.405898,
      "model_identifier": "speechbrain/spkrec-ecapa-voxceleb"
    }
  }
}
```

---

#### E. Threshold Configuration Management
- **List Threshold Configurations:** `GET /api/v1/admin/thresholds?skip=0&limit=50`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Response: `ApiResponse[List[ThresholdConfigResponse]]`
- **Get Active Threshold:** `GET /api/v1/admin/thresholds/active?model_identifier=...`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Response: `ApiResponse[Optional[ThresholdConfigResponse]]`
- **Create Threshold Configuration:** `POST /api/v1/admin/thresholds`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Payload:
```json
{
  "version_tag": "librispeech-eer-v1.1",
  "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
  "threshold_value": 0.420000,
  "calibration_dataset": "LibriSpeech test-clean",
  "calibration_criterion": "equal_error_rate_minimization",
  "calibration_metadata": { "eer": 0.048, "trials": 2000 },
  "is_active": false
}
```
  - Response: `ApiResponse[ThresholdConfigResponse]` (status 201)
- **Activate Threshold Configuration:** `POST /api/v1/admin/thresholds/{threshold_id}/activate`
  - Authorization: `ADMIN`, `SUPER_ADMIN`
  - Effects: Sets target threshold to `is_active=True`, deactivates other thresholds for that model, appends audit log.
  - Response: `ApiResponse[ThresholdConfigResponse]`

---

#### F. Global Audit Logs
- **Route:** `GET /api/v1/admin/audit-logs?skip=0&limit=50&action=...&resource_type=...&actor_user_id=...`
- **Authorization:** `ADMIN`, `SUPER_ADMIN`
- **Response Schema:** `ApiResponse[AdminAuditLogListResponse]`
```json
{
  "success": true,
  "message": "Audit logs retrieved.",
  "data": {
    "total": 250,
    "skip": 0,
    "limit": 50,
    "items": [
      {
        "id": "uuid",
        "actor_user_id": "uuid",
        "action": "USER_STATUS_UPDATED",
        "resource_type": "user",
        "resource_id": "user-uuid",
        "changes": { "is_active": false },
        "created_at": "2026-11-13T11:00:00Z"
      }
    ]
  }
}
```

---

#### G. Security Events & Rate-Limiting
- **Route:** `GET /api/v1/admin/security-events?skip=0&limit=50`
- **Authorization:** `ADMIN`, `SUPER_ADMIN`
- **Response Schema:** `ApiResponse[AdminSecurityEventsResponse]`
  - Aggregates security events from `audit_logs` (e.g. actions `USER_DEACTIVATED`, `USER_ROLES_MODIFIED`, `USER_DELETED`, `PASSWORD_CHANGED`, `CONSENT_REVOKED`, `PROFILE_REVOKED`, `TOKEN_REUSE`, `RATE_LIMIT_EXCEEDED`).
  - Includes current rate limiter configuration metadata:
    - Backend: `redis` / `in-memory`
    - Rate limit rules for login, registration, verification, enrollment, password_change.

