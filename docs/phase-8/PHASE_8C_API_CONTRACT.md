# Sentinel Voice — Phase 8C API Contract Audit & Specification

## 1. Overview
This document specifies the authoritative backend API contract for voice biometrics and legal consent in **Sentinel Voice**. Every frontend operation in Phase 8C maps directly to these verified FastAPI endpoints and Pydantic schemas.

---

## 2. Biometric Endpoints (`/api/v1/biometrics`)

### 2.1 Voiceprint Enrollment
- **Route**: `POST /api/v1/biometrics/enroll`
- **Authentication**: Required (`Bearer <access_token>` or HttpOnly session).
- **Rate Limit**: Default `3/hour` per user (`RateLimiter("enrollment", key_type="user")`).
- **Content-Type**: `multipart/form-data; boundary=...`
- **Request Parameters**:
  - `files` (`List[UploadFile]`): **At least 3 and at most 10** audio files.
  - Audio Format: **WAV or FLAC** (Header validated with `RIFF`/`WAVE` or `fLaC`).
  - Audio Constraints: Duration 1.0 to 60.0 seconds per file; Maximum size 10 MB per file; 16 kHz mono recommended.
- **Success Response**: `HTTP 201 Created`
  ```json
  {
    "profile_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "ACTIVE",
    "sample_count": 3,
    "mean_pairwise_similarity": 0.8842,
    "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
    "created_at": "2026-11-13T12:00:00Z",
    "samples": [
      {
        "duration_sec": 3.45,
        "rms_energy": 0.082,
        "peak_amplitude": 0.654,
        "audio_format": "WAV",
        "snr_db": 22.4
      }
    ]
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: `BiometricConsentRequiredError`, `InsufficientEnrollmentSamplesError` (< 3 files), or `InvalidEnrollmentAudioError` (duration < 1.0s or > 60.0s, invalid header, corrupted bytes).
  - `401 Unauthorized`: Missing or invalid JWT bearer token.
  - `409 Conflict`: `ActiveProfileAlreadyExistsError` (active profile already enrolled; must re-enroll or revoke first).
  - `429 Too Many Requests`: Rate limit exceeded.

---

### 2.2 Live Voice Verification
- **Route**: `POST /api/v1/biometrics/verify`
- **Authentication**: Required (`Bearer <access_token>`).
- **Rate Limit**: Default `20/hour` per user (`RateLimiter("verification", key_type="user")`).
- **Content-Type**: `multipart/form-data; boundary=...`
- **Request Parameters**:
  - `file` (`UploadFile`): **Single** probe audio recording.
  - Audio Format: **WAV or FLAC** (1.0 to 60.0 seconds, <= 10 MB).
- **Success Response**: `HTTP 200 OK`
  ```json
  {
    "verification_id": "1e2f3c4d-5678-90ab-cdef-1234567890ab",
    "decision": "MATCH",
    "is_match": true,
    "similarity_score": 0.842105,
    "applied_threshold": 0.405898,
    "processing_time_ms": 345.2,
    "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
    "threshold_version": "v1.0.0-eer-calibrated",
    "threshold_id": "77a80b12-9c31-4e78-8380-49658ec3429a",
    "timestamp": "2026-11-13T12:05:00Z"
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: `BiometricConsentRequiredError`, `InvalidEnrollmentAudioError` (corrupt or invalid audio).
  - `401 Unauthorized`: Expired or missing auth.
  - `404 Not Found`: `ProfileNotFoundError` (user has not enrolled yet).
  - `403 Forbidden`: `ProfileRevokedError` (user's profile has been revoked).
  - `429 Too Many Requests`: Rate limit exceeded.

---

### 2.3 Active Profile Retrieval
- **Route**: `GET /api/v1/biometrics/profile`
- **Authentication**: Required.
- **Success Response**: `HTTP 200 OK` (`VoiceProfileDetailResponse`)
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "ACTIVE",
    "sample_count": 3,
    "mean_pairwise_similarity": 0.8842,
    "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
    "created_at": "2026-11-13T12:00:00Z",
    "updated_at": "2026-11-13T12:00:00Z",
    "revoked_at": null,
    "enrollment_records": [
      {
        "duration_sec": 3.45,
        "rms_energy": 0.082,
        "peak_amplitude": 0.654,
        "audio_format": "WAV",
        "snr_db": 22.4
      }
    ]
  }
  ```
- **Error Responses**:
  - `404 Not Found`: No active profile enrolled for the caller.

---

### 2.4 Profile History
- **Route**: `GET /api/v1/biometrics/profile/history`
- **Query Parameters**: `skip` (default: 0), `limit` (default: 50, max: 100).
- **Success Response**: `HTTP 200 OK` -> `List[VoiceProfileResponse]`

---

### 2.5 Re-enrollment
- **Route**: `POST /api/v1/biometrics/profile/re-enroll`
- **Authentication**: Required.
- **Rate Limit**: `3/hour`.
- **Request Parameters**:
  - `files` (`List[UploadFile]`): 3 to 10 new enrollment audio recordings.
- **Workflow**:
  1. Identifies prior active profile and cryptographically shreds its AES-256-GCM vector container from disk.
  2. Marks previous profile as `REVOKED`.
  3. Enrolls new voiceprint and commits new reference centroid.
- **Success Response**: `HTTP 201 Created`
  ```json
  {
    "profile_id": "new-uuid",
    "previous_profile_id": "old-uuid",
    "status": "ACTIVE",
    "sample_count": 3,
    "mean_pairwise_similarity": 0.8912,
    "message": "Voiceprint re-enrollment successful. Previous profile was revoked and shredded."
  }
  ```

---

### 2.6 Profile Revocation
- **Route**: `DELETE /api/v1/biometrics/profile`
- **Authentication**: Required.
- **Workflow**:
  1. Sets active profile state to `REVOKED`.
  2. Executes multi-pass cryptographic shredding (NIST SP 800-88) of the vector file on disk.
  3. Records administrative audit event.
- **Success Response**: `HTTP 200 OK`
  ```json
  {
    "profile_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "status": "REVOKED",
    "revoked_at": "2026-11-13T12:15:00Z",
    "message": "Voice profile revoked and biometric vector shredded from storage."
  }
  ```

---

### 2.7 Verification Audit History
- **Route**: `GET /api/v1/biometrics/verification-history`
- **Query Parameters**:
  - `skip` (int, default: 0)
  - `limit` (int, default: 50, max: 100)
  - `decision` (optional string: `"MATCH"` or `"NO_MATCH"`)
  - `start_date` (optional ISO 8601 string)
  - `end_date` (optional ISO 8601 string)
  - `order` (string: `"desc"` or `"asc"`, default: `"desc"`)
- **Success Response**: `HTTP 200 OK`
  ```json
  {
    "total": 42,
    "skip": 0,
    "limit": 50,
    "items": [
      {
        "id": "event-uuid",
        "decision": "MATCH",
        "is_match": true,
        "similarity_score": 0.842105,
        "applied_threshold": 0.405898,
        "processing_time_ms": 345.2,
        "created_at": "2026-11-13T12:05:00Z",
        "threshold_id": "threshold-uuid",
        "client_ip": "127.0.0.1"
      }
    ]
  }
  ```

---

## 3. Biometric Consent Endpoints (`/api/v1/consent`)

### 3.1 Check Consent Status
- **Route**: `GET /api/v1/consent/me`
- **Response**: `ApiResponse[dict]`
  ```json
  {
    "success": true,
    "message": "Consent status retrieved successfully.",
    "data": {
      "has_active_consent": true,
      "current_consent": { ... },
      "history": [ ... ]
    }
  }
  ```

### 3.2 Grant Biometric Consent
- **Route**: `POST /api/v1/consent`
- **Payload**: `{"consent_version": "1.0", "consent_type": "VOICE_BIOMETRIC_ENROLLMENT"}`
- **Response**: `ApiResponse[ConsentResponse]` (`HTTP 201 Created`)

### 3.3 Revoke Biometric Consent
- **Route**: `POST /api/v1/consent/revoke`
- **Payload**: `{"consent_type": "VOICE_BIOMETRIC_ENROLLMENT", "reason": "User revoked"}`
- **Response**: `ApiResponse[ConsentResponse]` (`HTTP 200 OK`)

---

## 4. Key Architectural Invariants for Frontend Integration
1. **Multipart Upload Boundary**: Axios multipart requests must not manually set `Content-Type: multipart/form-data` without the boundary. Leaving `Content-Type` undefined lets the browser inject the correct `multipart/form-data; boundary=----...`.
2. **Audio Encoding Format**: The backend `validate_audio_header` strictly requires **WAV** (`RIFF` + `WAVE`) or **FLAC** (`fLaC`). The frontend audio recorder must encode recorded audio directly to standard 16-bit PCM WAV (16 kHz mono) before submission.
3. **No Persistent Client Storage**: Raw audio recordings must never be written to `localStorage`, `sessionStorage`, or `IndexedDB`. All temporary object URLs must be revoked upon component unmount or recording reset.
4. **No Fabricated Data**: Frontend components must never generate synthetic similarity scores, thresholds, or match decisions. All evaluation output is strictly server-driven.

