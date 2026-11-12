# Sentinel Voice — REST API Specification & OpenAPI Contract
**Document ID:** `DOC-P7-06`  
**Phase:** 7A (Standalone Application Architecture & System Design)  
**Status:** Approved Architecture Draft  

---

## 1. API Architecture & Versioning Strategy

All Sentinel Voice REST endpoints are anchored under the global URL prefix `/api/v1`. The API follows standard HTTP semantic verbs, status codes, and JSON error contracts adhering to RFC 7807.

### Authentication Headers
- **User JWT Bearer:** `Authorization: Bearer <access_token>`
- **Developer API Key:** `X-API-Key: sv_live_...` or `Authorization: Bearer sv_live_...`

---

## 2. Authentication & Session Endpoints (`/api/v1/auth`)

### 2.1 `POST /api/v1/auth/register`
Creates a new enterprise user account.

- **Access Level:** Public
- **Request Body (`application/json`):**
  ```json
  {
    "email": "analyst@enterprise.com",
    "password": "SecurePassword123!",
    "full_name": "Jane Doe"
  }
  ```
- **Response `201 Created`:**
  ```json
  {
    "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "email": "analyst@enterprise.com",
    "full_name": "Jane Doe",
    "is_active": true,
    "created_at": "2026-11-12T18:00:00Z"
  }
  ```

### 2.2 `POST /api/v1/auth/login`
Authenticates user credentials and issues an Access Token and Refresh Token.

- **Access Level:** Public
- **Request Body (`application/json`):**
  ```json
  {
    "email": "analyst@enterprise.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response `200 OK`:** Sets HTTP-only secure cookie `refresh_token` and returns:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in_sec": 900,
    "user": {
      "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "email": "analyst@enterprise.com",
      "full_name": "Jane Doe",
      "roles": ["ANALYST"]
    }
  }
  ```

### 2.3 `POST /api/v1/auth/refresh`
Rotates the refresh token and issues a fresh 15-minute access token.

- **Access Level:** Refresh Token Cookie (`refresh_token`)
- **Required Security Header:** `X-CSRF-Token: <csrf_token>` (Double-Submit Cookie protection)
- **Response `200 OK`:** Returns new `access_token` and sets rotated refresh cookie.

### 2.4 `POST /api/v1/auth/logout`
Revokes the active refresh token session in the database and clears cookies.

- **Access Level:** Authenticated User
- **Required Security Header:** `X-CSRF-Token: <csrf_token>`
- **Response `204 No Content`**
Revokes the active refresh token session in the database and clears cookies.

- **Access Level:** Authenticated User
- **Response `204 No Content`**

---

## 3. User Management Endpoints (`/api/v1/users`)

| Method | Endpoint | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/users/me` | Authenticated | Retrieve currently authenticated user profile and roles. |
| `PATCH` | `/api/v1/users/me` | Authenticated | Update user display name or preferences. |
| `GET` | `/api/v1/users` | Admin (`ADMIN`, `SUPER_ADMIN`) | Paginated, filterable directory of all system users. |
| `GET` | `/api/v1/users/{user_id}` | Admin or Self | Retrieve specific user account details. |
| `PATCH` | `/api/v1/users/{user_id}/status` | Admin | Activate or deactivate user account (`is_active: bool`). |
| `PUT` | `/api/v1/users/{user_id}/roles` | SuperAdmin | Assign or revoke user access roles. |

---

## 4. Voice Enrollment Endpoints (`/api/v1/enrollment`)

### 4.1 `POST /api/v1/enrollment`
Registers a reference voice profile for a user using exactly $K=3$ audio recordings and mandatory consent.

- **Access Level:** Authenticated (`ADMIN` or Self-Enrollment) / Scoped API Key (`enrollment:write`)
- **Request Format:** `multipart/form-data`
  - `user_id` (string, required): Target user ID.
  - `consent` (boolean, required): Must be `true` (biometric authorization).
  - `consent_version` (string, optional, default: `"v1.0"`).
  - `files` (array of binary audio files, required): Exactly 3 valid WAV or FLAC recordings.
- **Response `201 Created`:**
  ```json
  {
    "profile_id": "8f3b23e1-7c9d-4e8b-b1d5-998822ee44aa",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "status": "ACTIVE",
    "sample_count": 3,
    "mean_pairwise_similarity": 0.8842,
    "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
    "embedding_dimension": 192,
    "created_at": "2026-11-12T18:05:00Z"
  }
  ```

> [!CAUTION]
> **Biometric Privacy Violation Check:**  
> The 192D floating-point embedding vector is strictly omitted from `EnrollmentResponse`.

### 4.2 `GET /api/v1/enrollment/{profile_id}`
Retrieves public metadata and operational status for an enrolled profile.

- **Access Level:** Authenticated
- **Response `200 OK`:** Returns metadata identical to `201 Created` above.

### 4.3 `POST /api/v1/enrollment/{profile_id}/revoke`
Deactivates an active voice profile. Revoked profiles immediately fail all future verification attempts.

- **Access Level:** Admin or Self
- **Response `200 OK`:**
  ```json
  {
    "profile_id": "8f3b23e1-7c9d-4e8b-b1d5-998822ee44aa",
    "user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "status": "REVOKED",
    "revoked_at": "2026-11-12T18:10:00Z"
  }
  ```

### 4.4 `DELETE /api/v1/enrollment/{profile_id}`
Cryptographically deletes the profile record and wipes the physical `.npz` vector from disk (GDPR Article 17 "Right to Erasure").

- **Access Level:** Admin or Self
- **Response `204 No Content`**

---

## 5. Voice Verification Endpoints (`/api/v1/verification`)

### 5.1 `POST /api/v1/verification`
Executes real-time 1:1 speaker identity verification.

- **Access Level:** Authenticated / Scoped API Key (`verify`)
- **Request Format:** `multipart/form-data`
  - `claimed_user_id` (string, required): Identity claimed by claimant.
  - `audio_file` (binary, required): WAV or FLAC voice probe recording ($1.0\text{s} \le \text{duration} \le 60.0\text{s}$).
- **Response `200 OK`:**
  ```json
  {
    "verification_id": "d6187773-77cf-4e11-9a86-e5521938d95b",
    "claimed_user_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "profile_id": "8f3b23e1-7c9d-4e8b-b1d5-998822ee44aa",
    "decision": "MATCH",
    "is_match": true,
    "similarity_score": 0.815478,
    "applied_threshold": 0.405898,
    "processing_time_ms": 118.42,
    "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
    "timestamp": "2026-11-12T18:15:22Z"
  }
  ```

### 5.2 `GET /api/v1/verification/history`
Retrieves a paginated list of verification audit events.

- **Query Parameters:**
  - `page` (int, default: 1)
  - `page_size` (int, default: 20, max: 100)
  - `user_id` (string, optional)
  - `decision` (string: `'MATCH'` or `'NO_MATCH'`, optional)
  - `start_date` / `end_date` (ISO-8601 timestamps, optional)
- **Response `200 OK`:**
  ```json
  {
    "items": [ /* list of verification events */ ],
    "total_count": 2624,
    "page": 1,
    "page_size": 20,
    "total_pages": 132
  }
  ```

### 5.3 `GET /api/v1/verification/{verification_id}`
Retrieves complete forensic metadata for a specific verification event.

- **Response `200 OK`:** Detailed verification event metadata including audio duration, RMS energy, and client IP.

---

## 6. Dashboard & Analytics Endpoints (`/api/v1/dashboard`, `/api/v1/analytics`)

### 6.1 `GET /api/v1/dashboard/statistics`
Provides aggregated operational metrics for the main web dashboard.

- **Response `200 OK`:**
  ```json
  {
    "total_users": 1420,
    "total_enrolled_profiles": 1280,
    "active_profiles": 1245,
    "revoked_profiles": 35,
    "total_verifications_all_time": 48210,
    "verifications_past_24h": 1840,
    "successful_matches_past_24h": 1792,
    "failed_matches_past_24h": 48,
    "pass_rate_percentage": 97.39,
    "avg_processing_latency_ms": 112.5
  }
  ```

### 6.2 `GET /api/v1/analytics/benchmarks`
Exposes the published scientific research metrics (from Phase 5E) as read-only historical references.

- **Response `200 OK`:**
  ```json
  {
    "benchmark_corpus": "LibriSpeech (dev-clean & test-clean)",
    "calibrated_threshold": 0.405898,
    "test_accuracy_percent": 99.09,
    "test_far_percent": 0.28,
    "test_frr_percent": 1.02,
    "diagnostic_eer_percent": 0.56,
    "roc_auc": 0.9996,
    "confidence_intervals_95": {
      "accuracy": "[98.46%, 99.63%]",
      "far": "[0.00%, 1.64%]",
      "frr": "[0.39%, 1.77%]"
    }
  }
  ```

---

## 7. System Diagnostics (`/api/v1/health`, `/api/v1/model/status`)

### 7.1 `GET /api/v1/health`
System liveness and readiness probe for container orchestrators.

- **Response `200 OK`:**
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-11-12T18:20:00Z",
    "database": "connected",
    "biometric_storage": "writable"
  }
  ```

### 7.2 `GET /api/v1/model/status`
Neural network inference engine health and memory status.

- **Response `200 OK`:**
  ```json
  {
    "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
    "is_loaded": true,
    "device": "cpu",
    "embedding_dimension": 192,
    "calibrated_threshold": 0.405898
  }
  ```

### 7.3 `GET /api/v1/system/threshold`
Retrieves the currently active system verification threshold and provenance metadata.

- **Access Level:** Authenticated
- **Response `200 OK`:**
  ```json
  {
    "version_tag": "ecapa-voxceleb-v1.0",
    "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
    "threshold_value": 0.405898,
    "calibration_dataset": "LibriSpeech dev-clean",
    "calibration_criterion": "equal_error_rate_minimization",
    "is_active": true,
    "created_at": "2026-11-12T15:20:00Z"
  }
  ```

### 7.4 `PUT /api/v1/system/threshold`
Updates the operational verification threshold or activates a new calibration configuration.

- **Access Level:** SuperAdmin (`SUPER_ADMIN`)
- **Request Body (`application/json`):**
  ```json
  {
    "threshold_value": 0.405898,
    "version_tag": "custom-tuned-v1.1",
    "reason": "Administrative calibration update based on acoustic domain profile"
  }
  ```
- **Response `200 OK`:** Updated threshold configuration metadata.

