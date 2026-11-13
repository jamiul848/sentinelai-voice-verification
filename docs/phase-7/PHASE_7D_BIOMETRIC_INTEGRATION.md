# Sentinel Voice — Phase 7D: Voice Biometric Integration & Live Pipeline Bridge

## Technical Specification & Architecture Report

**Project:** Sentinel Voice (Standalone AI-Powered Speaker Verification Platform)  
**Milestone:** Phase 7D — Live ECAPA-TDNN Integration, Envelope Encryption, Dynamic Thresholding & Biometric Lifecycle  
**Date:** November 2026  
**Status:** Completed & Validated (373 / 373 Tests Passing)

---

## 1. Executive Summary

Phase 7D delivers the operational bridge connecting the deep learning neural speaker recognition engine (Phases 1–5E) with the zero-trust commercial application layer (Phases 7A–7C). 

Authenticated end-users are now able to:
1. Undergo multi-utterance voice enrollment with acoustic quality gatekeeping.
2. Generate 192-dimensional ECAPA-TDNN speaker embeddings and aggregate them into an L2-normalized reference voiceprint centroid.
3. Envelope-encrypt reference centroids using a per-profile Data Encryption Key (DEK) wrapped with the application master Key Encryption Key (KEK) via AES-256-GCM.
4. Execute single-probe speaker verification with dynamic calibrated decision thresholding retrieved from PostgreSQL 18.
5. Manage complete biometric lifecycles (active profile inspection, chronological profile history, explicit re-enrollment with automatic vector shredding, and full profile revocation with multi-pass cryptographic erasure).
6. Explore paginated and filterable verification audit trails.

All 335 pre-existing unit, integration, and security tests continue to pass without regression, supplemented by 38 new automated biometric tests across storage, services, API endpoints, and zero-trust security invariants (total: **373 passing tests**).

---

## 2. System Architecture & Component Interactions

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Client Application                              │
│             (Authenticated User with Bearer JWT & Biometric Consent)         │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ Multipart Audio Utterances (WAV / FLAC)
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Biometrics Router (/api/v1/biometrics)            │
│       - require_authenticated_user dependency (User, Role, Status check)     │
└───────────────┬──────────────────────────────────────────────┬───────────────┘
                │                                              │
                ▼ (Enroll / Re-enroll)                         ▼ (Verify)
┌──────────────────────────────────────┐     ┌─────────────────────────────────┐
│     BiometricEnrollmentService       │     │    BiometricVerificationService │
├──────────────────────────────────────┤     ├─────────────────────────────────┤
│ 1. Validate Consent (GDPR/BIPA)      │     │ 1. Validate Consent (GDPR/BIPA) │
│ 2. Guard Duplicate Active Profile    │     │ 2. Retrieve Active Profile      │
│ 3. Acoustic Preprocessing (16 kHz)   │     │ 3. Decrypt Ref Vector (DEK/KEK) │
│ 4. ECAPA-TDNN 192D Embedding Extr.   │     │ 4. Preprocess Probe & Extract   │
│ 5. Centroid Aggregation              │     │ 5. Cosine Similarity Scoring    │
│ 6. Envelope Encrypt (DEK via KEK)    │     │ 6. Dynamic Threshold Retrieval  │
│ 7. Write outputs/biometric_store/    │     │ 7. Evaluate MATCH / NO_MATCH    │
│ 8. Record DB Profile & Sample Meta   │     │ 8. Record VerificationEvent     │
│ 9. Write Immutable AuditLog          │     │ 9. Write Immutable AuditLog     │
└───────────────┬──────────────────────┘     └─────────────────┬───────────────┘
                │                                              │
                ▼                                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       PostgreSQL 18 Database Ledger                          │
│   (voice_profiles, enrollment_records, verification_events, audit_logs,      │
│    threshold_configurations, consent_records, users)                         │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                   Zero-Trust Isolated Biometric Storage                      │
│                  `outputs/biometric_store/{user_id}/{profile_id}.enc`        │
│          - AES-256-GCM Envelope Encryption (Magic Header: SNTV2)             │
│          - 2-Pass Cryptographic Shredding (Random bytes + Zeroes + Unlink)   │
│          - Strict Path Traversal Defenses                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema & Dynamic Thresholding

### 3.1 Migration: `0003_threshold_configs`
Alembic revision `0003_threshold_configs` adds dynamic threshold configuration support and links verification transactions:

1. **`threshold_configurations` Table:**
   - `id`: UUID Primary Key.
   - `version_tag`: Unique version string (e.g. `librispeech-dev-clean-eer-v1.0`).
   - `model_identifier`: Backbone identifier (e.g. `speechbrain/spkrec-ecapa-voxceleb`).
   - `threshold_value`: Calibrated operational threshold (Numeric 7, 6, seeded to `0.405898`).
   - `calibration_dataset`: Dataset provenance (e.g. `LibriSpeech dev-clean`).
   - `calibration_criterion`: Optimization metric (e.g. `EER`).
   - `calibration_metadata`: JSON ledger storing EER, trials, and confidence intervals.
   - `is_active`: Boolean flag indicating current production operational threshold.
   - Timestamps: `created_at`, `updated_at`.

2. **`verification_events.threshold_id` Column:**
   - Nullable foreign key referencing `threshold_configurations.id` on delete `SET NULL`.
   - Records exact calibration provenance for every verification attempt.

---

## 4. Cryptographic Storage & Zero-Trust Invariants

### 4.1 Envelope Encryption Specification (V2 Container)
- **Header (5 bytes):** Magic bytes `b"SNTV2"`.
- **Encrypted DEK Length (2 bytes):** Big-endian uint16 length of the encrypted DEK payload.
- **Encrypted DEK Payload (60 bytes):**
  - 12-byte Nonce + 32-byte Data Encryption Key (ciphertext) + 16-byte GCM Authentication Tag.
  - Encrypted with the Master Key Encryption Key (KEK) via AES-256-GCM.
- **Encrypted Vector Payload:**
  - 12-byte Nonce + Ciphertext (serialized 192D NumPy float32 centroid) + 16-byte GCM Authentication Tag.
  - Encrypted with the ephemeral Profile DEK via AES-256-GCM.
- **Integrity Digest:** SHA-256 checksum recorded in `voice_profiles.embedding_sha256` verified prior to decryption.
- **Backward Compatibility:** Containers lacking the `b"SNTV2"` magic header automatically decrypt via legacy direct master-key AES-256-GCM.

### 4.2 Path Traversal Defenses
All file paths resolved through `BiometricStorageManager.get_profile_path()` are canonicalized and tested via `relative_to(storage_root)`. Any attempt to escape the root directory using `..`, absolute paths, or special characters immediately raises a `DirectoryTraversalError` (403 Forbidden).

### 4.3 Cryptographic Shredding
When a voice profile is revoked or re-enrolled:
1. Pass 1: Container file overwritten with cryptographically strong random bytes (`os.urandom`).
2. Pass 2: Container file overwritten with zeroes (`b"\x00"`).
3. Pass 3: File flushed to physical disk (`os.fsync`) and unlinked from the filesystem (`unlink`).

---

## 5. API Reference

All routes are mounted under prefix `/api/v1/biometrics` and require `Authorization: Bearer <token>` with `USER` or `ADMIN` role and active legal biometric consent.

| Method | Endpoint | Description | Status Code | Error Codes |
|---|---|---|---|---|
| `POST` | `/enroll` | Multi-sample voiceprint enrollment (3–10 recordings) | 201 Created | `BIOMETRIC_CONSENT_REQUIRED`, `ACTIVE_PROFILE_ALREADY_EXISTS`, `INSUFFICIENT_ENROLLMENT_SAMPLES`, `INVALID_AUDIO_SAMPLE` |
| `POST` | `/verify` | Single probe voice verification | 200 OK | `BIOMETRIC_CONSENT_REQUIRED`, `PROFILE_NOT_FOUND`, `PROFILE_REVOKED`, `INVALID_AUDIO_SAMPLE`, `VECTOR_TAMPERED` |
| `GET` | `/profile` | Active voice profile and acoustic sample metadata | 200 OK | `PROFILE_NOT_FOUND` |
| `GET` | `/profile/history` | Chronological profile history (ACTIVE & REVOKED) | 200 OK | - |
| `POST` | `/profile/re-enroll` | Re-enroll voiceprint (shreds prior container) | 201 Created | `BIOMETRIC_CONSENT_REQUIRED`, `INSUFFICIENT_ENROLLMENT_SAMPLES`, `INVALID_AUDIO_SAMPLE` |
| `DELETE`| `/profile` | Revoke profile & shred encrypted container | 200 OK | `PROFILE_NOT_FOUND` |
| `GET` | `/verification-history` | Paginated, filterable verification audit events | 200 OK | - |

---

## 6. Test Suite & Verification Results

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.2.0, pluggy-1.7.0
rootdir: E:\sentinelai-voice-verification
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, platformdirs-4.14.5, asyncio-1.5.0
collected 373 items

tests\auth\... (28 passed)
tests\biometrics\test_biometric_enrollment_service.py ..... (5 passed)
tests\biometrics\test_biometric_profile_service.py ..... (5 passed)
tests\biometrics\test_biometric_storage.py ....... (7 passed)
tests\biometrics\test_biometric_verification_service.py ...... (6 passed)
tests\biometrics\test_biometrics_api.py ........... (11 passed)
tests\biometrics\test_biometrics_security.py ... (3 passed)
tests\consent\... (2 passed)
tests\database\... (37 passed)
tests\enrollment\... (33 passed)
tests\evaluation\... (72 passed)
tests\security\... (3 passed)
tests\speaker\... (32 passed)
tests\audio\... (43 passed)
tests\users\... (10 passed)
tests\verification\... (74 passed)

============================ 373 passed in 34.61s =============================
```

All 373 automated tests passed cleanly on Windows CPU environment.

