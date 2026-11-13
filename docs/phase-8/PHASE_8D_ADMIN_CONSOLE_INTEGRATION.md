# Phase 8D — Admin Console & System Monitoring Integration

**Document Version:** 1.0.0  
**Status:** COMPLETE & VERIFIED  
**Date:** 2026-11-13  
**Repository:** `E:\sentinelai-voice-verification`  
**Git Branch:** `feature/phase-8d-admin-console`  

---

## 1. Executive Summary

Phase 8D transforms the Sentinel Voice administrative foundation into an authoritative, enterprise-grade administration console and operational telemetry suite. All 9 administrative views are integrated with real FastAPI backend endpoints, PostgreSQL persistence, and diagnostic subsystem probes.

### Core Objectives Delivered
1. **Authoritative Backend RBAC Enforcement:** Every administrative endpoint (`/api/v1/admin/*` and `/health/detailed`) is strictly gated by FastAPI dependencies enforcing `ADMIN` or `SUPER_ADMIN` roles. Non-admin or unauthenticated requests are definitively rejected with `403 Forbidden` or `401 Unauthorized`.
2. **Zero Plaintext Biometric or Credential Leakage:** Administrative views strictly omit password hashes, raw audio buffers, floating-point embedding arrays, and cryptographic key material in adherence to ISO/IEC 30107-3 and NIST SP 800-88.
3. **Dynamic Threshold Governance:** Operating boundaries can be registered, evaluated, and activated dynamically at runtime with cosine range bound enforcement (`[-1.0, 1.0]`).
4. **Subsystem Diagnostic Probes:** Real-time health monitoring of PostgreSQL connection latency, Redis rate limiter state, ECAPA-TDNN PyTorch model cache, and biometric storage vault accessibility.
5. **Full Regression Integrity:** 87 passing frontend unit/integration tests (across 22 test files), zero ESLint errors, successful Next.js 16 production build, and 19/19 passing live HTTP end-to-end integration tests.

---

## 2. Security Model & RBAC Architecture

The Sentinel Voice security perimeter maintains a strict separation between client UX navigation routing and authoritative server-side access control:

```
+-------------------------------------------------------------------------+
|                              Client Layer                               |
|   Next.js 16 Client Router -> RouteGuard (UX Only) -> useAdmin Hooks   |
+-------------------------------------------------------------------------+
                                    |
                                    v HTTPS / TLS
+-------------------------------------------------------------------------+
|                           FastAPI Backend                               |
|   1. Request Tracing Middleware (X-Request-ID)                          |
|   2. Rate Limiting Middleware (Redis sliding-window / in-memory fallback)|
|   3. get_current_user (JWT verification & revocation check)             |
|   4. require_admin = require_role("ADMIN", "SUPER_ADMIN")               |
|      -> Rejects non-admins authoritatively with 403 Forbidden           |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                            Admin Service                                |
|   - Sanitized Projections (excludes secrets, hashes, vectors)           |
|   - Synchronous Audit Logging into PostgreSQL                           |
+-------------------------------------------------------------------------+
```

### Invariants Enforced
- **Server-Authoritative:** A manipulated or bypassed frontend client is blocked by FastAPI RBAC dependencies (`require_admin`).
- **Cryptographic Shredding:** Administrative revocation triggers NIST SP 800-88 compliant physical vector file overwriting via `BiometricStorageManager`.
- **Zero-Knowledge Principle:** Plaintext passwords, Argon2id hashes, raw audio arrays, and 192-dimensional floating-point vectors are never serialized in administrative API schemas.

---

## 3. Administrative Modules & Frontend Routes

### 3.1 Overview & Dashboard (`/admin/dashboard`)
- **8 Platform Metric Cards:** Total Registered Users, Active Users, Suspended Accounts, Active Voiceprints, Shredded Profiles, Total Verifications, Accepted Matches, Impostor Rejections.
- **Verification Decision Timeline:** 7-day and 30-day interactive volume visualization using Recharts.
- **Cluster Subsystems Health Banner:** Instant indicators for PostgreSQL 18, Redis Limiter, ECAPA-TDNN PyTorch engine, and AES-256-GCM vault.
- **Live Audit Stream:** Recent security audit events and status changes.

### 3.2 Identity & User Management (`/admin/users`)
- **Fleet Roster:** Filterable by status (Active/Suspended) and role (All/Admin/User), with debounced search by name, email, or UUID.
- **User Inspector Modal:** Full profile metadata without exposing credential hashes.
- **Status Mutation Modal:** Confirmation dialog for account suspension and reactivation.
- **RBAC Role Assignment Modal:** Interactive assignment of `USER`, `ADMIN`, and `SUPER_ADMIN` roles.
- **Permanent Account Deletion:** Confirmation dialog for permanent deletion with cascade cleanup.

### 3.3 Biometric Voiceprint Registry (`/admin/voice-profiles`)
- **Profile Inventory:** Enrolled centroids, intra-session consistency scores (mean pairwise cosine similarity), sample counts, and neural backbone identifier.
- **Administrative Revocation & Shredding Modal:** Triggers synchronous physical vector file shredding and status update to `REVOKED`.
- **Privacy Assurance Callout:** Explicit banner highlighting zero raw audio storage.

### 3.4 Verification Performance & Latency Analytics (`/admin/analytics`)
- **KPI Metrics:** Total verification volume, operational match rate, NO_MATCH impostor block rate, and mean processing latency in milliseconds.
- **Time Window Filtering:** Toggle between 7-day, 14-day, 30-day, and 90-day aggregation windows.
- **Active Threshold Reference:** Displays the active version tag, cosine boundary, calibration dataset provenance, and optimization criteria.

### 3.5 Dynamic Threshold Governance (`/admin/thresholds`)
- **Active Decision Boundary Banner:** Real-time active threshold configuration and model identifier.
- **Registered Boundaries Ledger:** Complete history of calibrated thresholds with empirical EER provenance.
- **Registration Modal:** Form validating version tag, empirical EER, neural model, and cosine operating boundary strictly bounded within `[-1.0, 1.0]`.
- **Activation Modal:** Atomic activation updating the active threshold in PostgreSQL and synchronizing the verification engine.

### 3.6 Global Immutable Audit Trail (`/admin/audit-logs`)
- **Tamper-Proof Audit Ledger:** Chronological immutable records of all authentication events, user status mutations, role modifications, threshold activations, and biometric revocations.
- **Search & Category Filters:** Filter by category (User, Voiceprint, Consent, Threshold) or free-text query.
- **Sanitized Record Inspector:** Modal displaying change diffs without exposing credentials or tokens.

### 3.7 Diagnostic Probes & System Health (`/admin/system-health`)
- **Cluster Status Banner:** Service name, version, and uptime calculation.
- **PostgreSQL 18 Subsystem Card:** Direct query probe returning millisecond round-trip latency and asyncpg pool state.
- **Redis Cache & Limiter Card:** Connection status, sliding window architecture, and failover indicator.
- **ECAPA-TDNN Neural Engine Card:** Non-loading inspection verifying model cache state without cold-start memory spikes.
- **Biometric Vault Card:** Filesystem write permissions and NIST SP 800-88 shredding support.
- **Envelope Encryption Card:** Configuration status of AES-256-GCM cryptographic master envelope.

### 3.8 Security Incident Ledger (`/admin/security-events`)
- **Rate Limiter Telemetry:** Active backend (`redis` or `in-memory fallback`) and quota rules (`POST /auth/login: 5/min`, `POST /auth/register: 3/hour`, etc.).
- **Security Incident Log:** Failed authentication bursts, privilege mutations, and rate limit triggers.

### 3.9 Platform Configuration (`/admin/settings`)
- **Platform Identity:** Node identifier, environment (`production`), API version (`/api/v1`).
- **Neural Architecture Hyperparameters:** SpeechBrain ECAPA-TDNN VoxCeleb backbone, 16kHz mono sampling, 80-channel Mel filterbanks, 192-dimensional embeddings.
- **Active Threshold Provenance:** Current operating boundary provenance.
- **Cryptographic Storage Governance:** AES-256-GCM envelope encryption specifications.

---

## 4. API Endpoints Contract

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/admin/overview` | Platform-wide fleet metrics and health summary | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/users` | List registered system accounts | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/users/{user_id}` | Fetch user details by UUID | `ADMIN` / `SUPER_ADMIN` |
| `PATCH` | `/api/v1/admin/users/{user_id}/status` | Activate or suspend user account | `ADMIN` / `SUPER_ADMIN` |
| `PATCH` | `/api/v1/admin/users/{user_id}/roles` | Assign RBAC roles | `ADMIN` / `SUPER_ADMIN` |
| `DELETE` | `/api/v1/admin/users/{user_id}` | Delete user account | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/voice-profiles` | List biometric voiceprint registry | `ADMIN` / `SUPER_ADMIN` |
| `POST` | `/api/v1/admin/voice-profiles/{id}/revoke` | Revoke profile & shred embeddings | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/analytics` | Verification analytics and score timeline | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/thresholds` | List all threshold configurations | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/thresholds/active` | Get active operational threshold | `ADMIN` / `SUPER_ADMIN` |
| `POST` | `/api/v1/admin/thresholds` | Register calibrated threshold | `ADMIN` / `SUPER_ADMIN` |
| `POST` | `/api/v1/admin/thresholds/{id}/activate` | Activate operational threshold | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/audit-logs` | Query global audit trail | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/api/v1/admin/security-events` | Security incidents and rate limiters | `ADMIN` / `SUPER_ADMIN` |
| `GET` | `/health/detailed` | Detailed cluster diagnostic probes | `ADMIN` / `SUPER_ADMIN` |

---

## 5. Verification & Test Evidence

### Frontend Unit & Integration Tests (Vitest)
- **Total Test Files:** 22
- **Total Passing Tests:** 87
- **Test File Breakdown:**
  - `src/test/admin-access.test.tsx` (4 tests) — Authorization guards & non-admin redirection
  - `src/test/admin-api.test.ts` (11 tests) — Admin API service contract execution
  - `src/test/admin-dashboard.test.tsx` (3 tests) — 8 statistic cards & subsystem indicators
  - `src/test/admin-users.test.tsx` (5 tests) — User roster, search, status, roles, deletion
  - `src/test/admin-voice-profiles.test.tsx` (3 tests) — Registry display, search, shredding
  - `src/test/admin-thresholds.test.tsx` (3 tests) — Threshold registration, activation, banners
  - `src/test/admin-analytics.test.tsx` (3 tests) — Analytics KPIs, time window selection
  - `src/test/admin-audit-logs.test.tsx` (3 tests) — Audit records, category filters, detail inspector
  - `src/test/admin-health.test.tsx` (2 tests) — Diagnostic probes & health refetching
  - `src/test/admin-security-events.test.tsx` (1 test) — Rate limiter rules & incident ledger
  - *Plus 49 pre-existing tests across Auth, Navigation, Biometrics, and Dashboard*

### ESLint & TypeScript Compilation
- **ESLint:** 0 errors, 40 warnings (clean compilation).
- **Next.js 16 Production Build:** All 22 routes compiled successfully and prerendered as static content.

### Live End-to-End HTTP Integration Suite (`tests/verify_phase_8d_live.py`)
- **Total Live Steps Executed:** 19
- **Passing Assertions:** 19/19 (100% Success)
- **Key Live Assertions Verified:**
  - Authoritative 403 Forbidden rejection across all 9 admin routes for standard operators.
  - Successful admin registration and database role promotion.
  - Platform overview data integrity verification.
  - Account deactivation and reactivation state transitions.
  - Non-leaking credential projections (zero password hashes in user payloads).
  - Non-leaking vector projections (zero raw floats or file paths in voice profile responses).
  - Dynamic threshold registration, cosine range boundary validation (422 rejection on cosine > 1.0), and activation synchronization.
  - Audit log query execution without token leakage in event payloads.
  - Diagnostic health probe verification (`database`, `redis`, `ecapa_engine`, `biometric_storage`, `encryption_service`).
  - Disposable user permanent deletion lifecycle.

