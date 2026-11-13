# Sentinel Voice — Phase 7C: Authentication & User Management

## Technical Specification & Architecture Report

**Project:** Sentinel Voice (Standalone AI-Powered Speaker Verification Platform)  
**Milestone:** Phase 7C — Authentication, Session Lifecycle, RBAC & Biometric Consent  
**Date:** November 2026  
**Status:** Completed & Validated (335 / 335 Tests Passing)

---

## 1. Executive Summary

Phase 7C establishes the commercial authentication, authorization, user management, and legal biometric consent layer for Sentinel Voice. Building atop the PostgreSQL 18 and SQLAlchemy 2.0 async database layer delivered in Phase 7B, Phase 7C implements zero-trust credential handling, Argon2id memory-hard password hashing, dual-token JWT and rotating refresh token session management, fine-grained server-side Role-Based Access Control (RBAC), and GDPR Article 7 / Illinois BIPA compliant biometric consent management.

All research assets (Phase 1–5E audio preprocessing, ECAPA-TDNN feature extraction, voice enrollment, LibriSpeech calibrated speaker verification engine) remain intact.

---

## 2. Authentication Architecture

### 2.1 Security Invariants
1. **Zero Plaintext Storage:** Passwords are hashed with Argon2id; refresh tokens are persisted solely as SHA-256 hashes.
2. **Decoupled Biometric Storage:** Biometric embeddings remain encrypted via AES-256-GCM and are never returned or reachable through authentication APIs.
3. **No Credential Leakage:** Failed authentication attempts return uniform error messages (`INVALID_CREDENTIALS`) in constant time to prevent account enumeration.
4. **Anti-Escalation Safeguards:** New user registration strictly assigns the `USER` role; administrative privileges cannot be self-assigned.
5. **Last Administrator Protection:** The system strictly prohibits the deactivation, demotion, or deletion of the last remaining active administrator.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Client Applications                             │
│       (Web Browser / Mobile App / API Client / External Microservice)  │
└──────────────────┬─────────────────────────────────┬───────────────────┘
                   │ Authorization: Bearer <jwt>     │ POST /auth/login
                   ▼                                 ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│       FastAPI Route Dependency       │  │       AuthService            │
│   (get_current_user / require_role)  │  │  - Argon2id Password Verify  │
├──────────────────────────────────────┤  │  - Issue JWT Access Token    │
│  - PyJWT Signature & Expiration Check│  │  - Generate Opaque Refresh   │
│  - Load User & Roles from DB         │  │  - SHA-256 Hash Refresh      │
│  - Verify is_active == True          │  │  - Double-Submit CSRF Cookie │
└──────────────────┬───────────────────┘  └──────────────┬───────────────┘
                   ▼                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL 18 Database                          │
│   (users, roles, user_roles, refresh_tokens, consent_records, audit)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Workflows

### 3.1 User Registration Workflow
* **Endpoint:** `POST /api/v1/auth/register`
* **Input Validation:**
  * Email format validated and normalized (trimmed, lowercased).
  * Password complexity enforced (minimum 8 characters, uppercase, lowercase, digit, special character).
  * Password and confirmation match.
  * Explicit acceptance of privacy terms required.
* **Execution:**
  1. Checks for existing user with identical email (`409 Conflict` on duplicate).
  2. Computes Argon2id hash (`$argon2id$v=19$m=65536,t=3,p=2$...`).
  3. Inserts user into `users` table (`is_active=True`, `is_verified=False`).
  4. Automatically resolves and assigns the default `USER` role via `user_roles`.
  5. Records append-only audit event `USER_REGISTERED`.
  6. Returns sanitized `UserResponse` (`201 Created`).

### 3.2 User Login & Token Issuance Workflow
* **Endpoint:** `POST /api/v1/auth/login`
* **Execution:**
  1. Queries user by lowercased email.
  2. Executes timing-safe Argon2id hash verification.
  3. Verifies account `is_active` status (`403 Forbidden` if inactive).
  4. Issues short-lived JWT access token (15-minute expiration) containing user UUID, email, assigned roles, and `jti`.
  5. Generates high-entropy opaque refresh token (48-byte URL-safe string).
  6. Computes SHA-256 hash of refresh token and stores in `refresh_tokens` table.
  7. Generates double-submit CSRF token.
  8. Sets cookies:
     * `sentinel_refresh_token`: `HttpOnly=True`, `SameSite=Lax`, `Secure` in production.
     * `sentinel_csrf_token`: `HttpOnly=False`, `SameSite=Lax`.
  9. Logs audit event `USER_LOGIN`.
  10. Returns `TokenResponse` and sanitized user profile.

### 3.3 Refresh Token Rotation & Breach Detection
* **Endpoint:** `POST /api/v1/auth/refresh`
* **Execution:**
  1. Hashes incoming raw refresh token with SHA-256.
  2. Queries `refresh_tokens` record.
  3. **Breach Detection:** If `is_revoked == True`, an attacker is attempting to reuse an invalidated token. The system:
     * Immediately revokes all active refresh tokens for that user ID (family revocation).
     * Logs high-priority audit event `TOKEN_REUSE_DETECTED`.
     * Rejects request with `401 Unauthorized`.
  4. **Expiration Check:** If `expires_at < utc_now()`, revokes token and rejects request.
  5. **Rotation:** Marks current token as revoked (`is_revoked=True`, `revoked_at=utc_now()`).
  6. Generates fresh refresh token pair, stores new hash, issues new JWT access token.
  7. Logs audit event `TOKEN_ROTATED`.

### 3.4 User Logout
* **Endpoint:** `POST /api/v1/auth/logout`
* **Execution:**
  1. Revokes provided refresh token or all user active sessions.
  2. Clears client session cookies.
  3. Logs audit event `USER_LOGOUT`.
  4. Operation is idempotent and safe against repeated calls.

---

## 4. Role-Based Access Control (RBAC)

RBAC is enforced strictly server-side using FastAPI dependencies:

| Role | Permissions & Scopes |
| :--- | :--- |
| **SUPER_ADMIN** | Complete platform bypass; manages all system configurations, roles, and administrative users. |
| **ADMIN** | User management (`/admin/users`), user role assignment, user activation/deactivation, audit trail inspection. |
| **ANALYST** | Evaluation analysis, trial scoring, and metrics inspection. |
| **USER / END_USER** | Audio upload, voice enrollment, verification, profile retrieval, password modification, and consent management. |

### Dependency Guards
* `require_authenticated_user`: Ensures valid JWT and active account status.
* `require_role(*allowed_roles)`: Enforces role membership with `SUPER_ADMIN` inheritance.
* `require_admin`: Shorthand for `require_role("ADMIN", "SUPER_ADMIN")`.

---

## 5. Biometric Legal Consent Management

In compliance with GDPR Article 7 and Illinois BIPA:
* **Grant Consent (`POST /api/v1/consent`):** Explicitly records user consent version, scope, IP address, and timestamp in `consent_records`.
* **View Consent (`GET /api/v1/consent/me`):** Returns whether user has active consent and the full immutable chronological history.
* **Revoke Consent (`POST /api/v1/consent/revoke`):**
  1. Records revocation event in `consent_records` (`consent_granted=False`).
  2. Automatically identifies active `VoiceProfile`.
  3. Transitions profile status to `REVOKED`.
  4. Triggers multi-pass cryptographic file shredding via `secure_delete_file()` to permanently overwrite and unlink the AES-256-GCM encrypted vector file from storage.
  5. Logs audit event `PROFILE_REVOKED_CONSENT_WITHDRAWN`.

---

## 6. API Endpoint Reference

| Method | Path | Summary | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/auth/register` | Register new user account | None |
| `POST` | `/api/v1/auth/login` | Authenticate and issue token pair | None |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token | Refresh Token |
| `POST` | `/api/v1/auth/logout` | Revoke session and clear cookies | None / Optional |
| `GET` | `/api/v1/users/me` | Get authenticated user profile | Bearer Token |
| `PATCH` | `/api/v1/users/me` | Update permitted profile fields | Bearer Token |
| `POST` | `/api/v1/users/change-password` | Change password & revoke sessions | Bearer Token |
| `GET` | `/api/v1/admin/users` | List users paginated | Admin Role |
| `GET` | `/api/v1/admin/users/{id}` | Inspect user details | Admin Role |
| `PATCH` | `/api/v1/admin/users/{id}/status` | Activate / deactivate user | Admin Role |
| `PATCH` | `/api/v1/admin/users/{id}/roles` | Assign RBAC roles | Admin Role |
| `DELETE` | `/api/v1/admin/users/{id}` | Delete user account | Admin Role |
| `POST` | `/api/v1/consent` | Grant explicit biometric consent | Bearer Token |
| `GET` | `/api/v1/consent/me` | View consent status and timeline | Bearer Token |
| `POST` | `/api/v1/consent/revoke` | Revoke consent & shred biometric data | Bearer Token |

---

## 7. Database Changes & Alembic Migration

### Migration: `0002_allow_consent_revocation`
* **File:** `migrations/versions/0002_allow_consent_revocation.py`
* **Purpose:** Drops PostgreSQL check constraint `check_consent_granted_true` on table `consent_records`.
* **Rationale:** Allows immutable recording of revocation transactions (`consent_granted=FALSE`), preserving the complete legal timeline without overwriting past consent decisions.
* **Applied to Live Database:** Verified and active on PostgreSQL 18 `sentinel_voice`.

---

## 8. Verification & Test Execution Results

The comprehensive test suite verifies all layers:

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.2.0, pluggy-1.7.0
rootdir: E:\sentinelai-voice-verification
configfile: pyproject.toml
plugins: anyio-4.16.0, platformdirs-4.14.5, asyncio-1.5.0
asyncio: mode=Mode.AUTO

335 passed in 40.43s
============================= 335 passed =============================
```

### Breakdown of Passing Tests:
* **Audio Preprocessing & ECAPA Pipeline (Phases 1–2):** 52 tests
* **Enrollment & Verification Engine (Phases 3–4):** 78 tests
* **Dataset Evaluation & Calibration (Phases 5A–5E):** 126 tests
* **Database Models, Repositories & Migrations (Phase 7B):** 36 tests
* **Authentication, RBAC, User & Consent Management (Phase 7C):** 43 tests
  * `test_jwt.py`: 5 tests
  * `test_login.py`: 4 tests
  * `test_logout.py`: 2 tests
  * `test_password_security.py`: 9 tests
  * `test_refresh_tokens.py`: 3 tests
  * `test_registration.py`: 5 tests
  * `test_rbac.py`: 6 tests
  * `test_user_management.py`: 4 tests
  * `test_consent_management.py`: 2 tests
  * `test_auth_security.py`: 3 tests

