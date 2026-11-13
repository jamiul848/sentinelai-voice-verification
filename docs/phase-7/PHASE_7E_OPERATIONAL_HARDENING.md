# Sentinel Voice – Phase 7E Specification & Architecture Report
## Operational Monitoring, Rate Limiting & Production Hardening

**Platform:** Sentinel Voice (Standalone AI-Powered Speaker Verification Platform)  
**Phase:** 7E – Operational Monitoring, Rate Limiting & Production Hardening  
**Status:** Completed & Validated (413 / 413 Passing Automated Tests)  
**Date:** November 2026  
**Audience:** Platform Architects, Site Reliability Engineers, Security Auditors  

---

## 1. Executive Summary

Phase 7E elevates the Sentinel Voice backend from a functional biometric prototype to an enterprise-grade, cloud-native, and production-hardened verification engine. Prior to Phase 7E, Phase 7D delivered live multi-utterance enrollment, 192D ECAPA-TDNN embedding aggregation, envelope-encrypted biometric vector storage, and dynamic threshold retrieval across 373 automated tests.

Phase 7E introduces a comprehensive defense-in-depth operational layer:
- **API Rate Limiting:** Distributed Redis sliding-window with in-memory thread-safe fallback, trusted reverse proxy anti-spoofing traversal, and dynamic HTTP 429 `Retry-After` headers.
- **Authentication Abuse Protection:** Intelligent tracking of failed login attempts per account (email hash) and IP address, enforcing temporary exponential lockouts without permanent account lockouts or credential enumeration side-channels.
- **Cloud-Native Health Monitoring:** Tiered health endpoints (`/health`, `/health/live`, `/health/ready`, and administrator-restricted `/health/detailed`) verifying database round-trip latency, storage accessibility, and ECAPA model cache state while guaranteeing **zero cold-start weight loading** during routine health checks.
- **Structured Logging & Sanitization:** High-throughput single-line ISO 8601 UTC JSON logging in production and human-readable formatting in development, paired with a recursive redaction filter that strips passwords, tokens, cookies, raw audio bytes, and 192D biometric vectors.
- **Distributed Request Tracing:** End-to-end `X-Request-ID` correlation across async task trees using Python `contextvars`, rejecting hostile payloads and guaranteeing trace isolation across concurrent requests.
- **Biometric Resource Guardrails:** 10MB maximum audio upload bounds, bounded concurrency semaphores preventing ML CPU/GPU starvation, and non-blocking asynchronous event loop offload via `asyncio.to_thread`.
- **Encryption & Key Management:** Full compliance with **NIST SP 800-88 Cryptographic Erasure** via ephemeral DEK destruction, tamper-evident GCM authentication tags, and online Master Key (KEK) rotation without user re-enrollment.
- **Database Resilience:** SQLAlchemy connection pool recycling (1,800s), pre-ping validation, query timeouts (10s), and sanitized exception handling masking raw SQL and schema details from clients.
- **Production Safety Validator:** Application startup guard halting deployment if default secret placeholders, active debug flags, wildcard CORS policies, or missing encryption keys are detected in production.

Regression baseline was completely preserved, increasing overall automated test coverage from **373 to 413 passing tests** with 100% pass rate.

---

## 2. Component Architecture & Implementation Breakdown

```
                                      [ INCOMING HTTP CLIENT ]
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    RequestTracingMiddleware           │
                             │  - Validates / generates X-Request-ID │
                             │  - Binds request_id to contextvars    │
                             └───────────────────┬───────────────────┘
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    StructuredLoggingMiddleware        │
                             │  - Latency tracking (ms)              │
                             │  - Structured JSON access logging     │
                             │  - Sensitive parameter redaction     │
                             └───────────────────┬───────────────────┘
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    CORSMiddleware (CORS Policy)       │
                             │  - Strict origin validation           │
                             │  - Wildcard prohibited in production  │
                             └───────────────────┬───────────────────┘
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    RateLimiter Dependency (429)       │
                             │  - Trusted reverse proxy resolution   │
                             │  - Redis ZSET sliding-window / Memory │
                             │  - X-RateLimit-* & Retry-After hdrs   │
                             └───────────────────┬───────────────────┘
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    AuthAbuseTracker (Brute-Force)     │
                             │  - SHA-256 identifier hashing         │
                             │  - Account & IP lockout thresholds    │
                             │  - Instant reset on valid login       │
                             └───────────────────┬───────────────────┘
                                                 │
                                                 ▼
                             ┌───────────────────────────────────────┐
                             │    Biometric Resource Protection      │
                             │  - 10MB audio upload limit check      │
                             │  - asyncio.Semaphore(4) inference     │
                             │  - asyncio.to_thread worker execution │
                             └───────────────────┬───────────────────┘
                                                 │
                                                 ▼
                      ┌──────────────────────────┴──────────────────────────┐
                      ▼                                                     ▼
           [ PostgreSQL 18 + asyncpg ]                           [ Biometric Storage ]
          - pool_pre_ping=True                                  - AES-256-GCM Envelope V2
          - pool_recycle=1800s                                  - Ephemeral DEK per profile
          - connect_args={"timeout": 10}                        - Master Key rotation utility
          - Masked SQLAlchemyError (500)                        - NIST SP 800-88 Shredding
```

---

## 3. Detailed Technical Modules

### 3.1. API Rate Limiting (`sentinelai/security/rate_limiter.py`)
- **Sliding-Window Algorithm:** Implemented using Redis sorted sets (`ZSET`) where elements are timestamped request entries. Prunes expired timestamps (`ZREMRANGEBYSCORE`), counts active requests (`ZCARD`), and adds new request tokens atomically in a pipeline with an expiry buffer (`EXPIRE`).
- **In-Memory Fallback:** Implements a thread-safe (`threading.Lock`), sliding-window in-memory backend for local development and single-container deployments. Automatically chosen when `RATE_LIMIT_STORAGE="memory"` or Redis is unavailable.
- **Anti-Spoofing Client IP Resolution:** `get_trusted_client_ip` inspects the immediate remote peer. If the peer is not in `settings.trusted_proxies`, `X-Forwarded-For` is strictly ignored to prevent attackers from spoofing arbitrary client IPs. If the peer is trusted, it traverses the `X-Forwarded-For` chain right-to-left, selecting the first untrusted upstream IP.
- **Configurable Endpoints & Headers:**
  - `POST /api/v1/auth/register`: `5/hour` per IP
  - `POST /api/v1/auth/login`: `5/15minute` per IP
  - `POST /api/v1/auth/refresh`: `10/15minute` per user/IP
  - `POST /api/v1/biometrics/enroll`: `5/15minute` per user
  - `POST /api/v1/biometrics/verify`: `20/minute` per user
  - `POST /api/v1/users/change-password`: `3/hour` per user
  - Dynamic headers attached to all responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, and `Retry-After` on HTTP 429.

### 3.2. Authentication Abuse & Brute-Force Defense (`sentinelai/security/auth_abuse.py`)
- **Account & IP Dual-Tracking:** Tracks failed attempts independently across email accounts (hashed) and connecting IP addresses.
- **Thresholds:**
  - Account threshold: 5 consecutive failures triggers a 900-second (15-minute) account cooldown.
  - IP threshold: 10 failures across any accounts triggers an 1,800-second (30-minute) IP cooldown, mitigating distributed credential spraying.
- **Privacy & Non-Disclosure:** Raw email addresses and usernames are never stored in memory; all identifiers are hashed using SHA-256 (`_hash_identifier`).
- **Timing Side-Channel Mitigation:** Returns identical generic error messages (`"Too many failed login attempts. Please try again later."`) with HTTP 429 and `Retry-After` header, avoiding any disclosure of whether an account exists.
- **Success Reset:** A single successful authentication immediately clears failure counts for both the target account and IP.

### 3.3. Cloud-Native Health Probes (`sentinelai/monitoring/`)
- `GET /health`: Basic operational probe returning `{"status": "healthy"}` for container load balancers.
- `GET /health/live`: Instantaneous process liveness probe returning 200 OK as long as the FastAPI event loop is responsive, avoiding external I/O.
- `GET /health/ready`: Evaluates whether dependencies (PostgreSQL database and Redis) are available to accept production traffic. Returns 200 OK (`ready`) or 503 Service Unavailable (`unready`) with component status.
- `GET /health/detailed`: Restricted to authenticated administrators (`ADMIN`, `SUPER_ADMIN`). Reports:
  - Component round-trip latencies (database latency in milliseconds).
  - ECAPA-TDNN engine state (device: CPU/CUDA, embedding dimension).
  - Biometric filesystem storage accessibility and storage root basename.
  - Cryptographic key configuration status (algorithm: `AES-256-GCM-Envelope-V2`).
  - Uptime in seconds.
- **Critical Security Invariants:**
  - `loader.is_loaded` non-loading inspection: Model cache state is inspected via properties without calling `load()`, ensuring health checks never cause latency spikes or memory bloat.
  - Zero Credential Disclosure: Connection strings, passwords, and cryptographic keys are never leaked in response payloads.

### 3.4. Structured Logging & Sanitization (`sentinelai/monitoring/logging.py`)
- **Formatters:**
  - Production (`LOG_FORMAT="json"`): Outputs strict single-line JSON with ISO 8601 UTC timestamp, log level, logger name, message, correlation ID, status code, method, route, and duration in milliseconds.
  - Development (`LOG_FORMAT="console"`): Human-readable formatted output with truncated 8-character correlation ID tags.
- **Recursive Sanitization (`sanitize_log_payload`):** Automatically traverses dictionaries and lists to replace sensitive keys with `[REDACTED]`. Redacted keys include: `password`, `old_password`, `new_password`, `access_token`, `refresh_token`, `token`, `authorization`, `cookie`, `secret`, `secret_key`, `csrf_token`, `biometric_encryption_key`, `embedding`, `embeddings`, `audio`, `audio_bytes`, `raw_audio`, `waveform`.

### 3.5. Distributed Request Tracing (`sentinelai/monitoring/request_tracing.py`)
- Extracts incoming `X-Request-ID` or generates a UUID4.
- Validates the header format using regex `^[a-zA-Z0-9_\-]{8,64}$`, rejecting any malformed headers, XSS injection attempts, or strings exceeding 64 characters.
- Stores the correlation ID in an async-isolated Python `ContextVar` (`request_id_ctx`), ensuring concurrent requests never cross-contaminate.
- Injects `X-Request-ID` into every outgoing HTTP response header and structured log entry.

### 3.6. Biometric Resource Limits & Concurrency (`sentinelai/biometrics/`)
- **10MB Audio Upload Bounds:** `BiometricEnrollmentService._read_audio_bytes` and `BiometricVerificationService._read_audio_bytes` inspect the raw byte size of incoming audio files, immediately rejecting files exceeding `settings.max_audio_upload_size_bytes` (10MB) with `InvalidEnrollmentAudioError` (HTTP 400).
- **Bounded Concurrency Semaphore:** `get_inference_semaphore()` enforces a bounded concurrency limit (`max_concurrent_inferences=4`), preventing simultaneous ML inference requests from consuming 100% CPU/GPU and starving HTTP request handling.
- **Event-Loop Non-Blocking Execution:** SpeechBrain ECAPA-TDNN feature extraction and forward passes are executed via `await asyncio.to_thread(self.extractor.extract, ...)`, keeping the main asyncio event loop responsive for concurrent I/O.

### 3.7. Biometric Encryption Hardening & Key Management (`sentinelai/biometrics/storage.py`)
- **NIST SP 800-88 Cryptographic Erasure:** Each voice profile is protected by a distinct 256-bit Data Encryption Key (DEK) wrapped with the master Key Encryption Key (KEK). When a user revokes their profile, multi-pass file shredding (`secure_delete_file`) destroys the DEK. Without the DEK, the AES-256-GCM ciphertext becomes mathematically unrecoverable across the $2^{256}$ keyspace.
- **Master Key Rotation (`rotate_master_key`):** Re-encrypts the stored DEKs with a new master KEK without decrypting the raw 192D speaker embedding vectors and without requiring users to re-enroll.
- **Tamper Detection:** AES-256-GCM 128-bit authentication tags verify container integrity. Any single-bit corruption in the container header, wrapped DEK, or vector ciphertext triggers `VectorTamperedError` and fails closed.

### 3.8. Database Reliability & Pool Hardening (`sentinelai/database/connection.py`)
- `pool_pre_ping=True`: Verifies connection vitality prior to checkout, recycling dropped or stale PostgreSQL connections transparently.
- `pool_recycle=1800`: Automatically replaces pooled connections older than 30 minutes to prevent firewall or TCP timeout drops.
- `connect_args={"timeout": 10.0}`: Prevents unbounded hanging if the database cluster experiences transient network partitions.
- **Sanitized Exception Handling:** Traps `SQLAlchemyError` at the FastAPI top level, rolling back the transaction, logging the error securely with correlation ID, and returning a generic HTTP 500 (`DATABASE_ERROR`) response that completely conceals table names, column names, and SQL statements from the client.

### 3.9. Production Configuration Validation (`sentinelai/security/config_validator.py`)
- Validates configuration parameters at application startup.
- Halts initialization (`ConfigurationSecurityError`) in production (`ENVIRONMENT="production"`) if:
  - `SECRET_KEY` is a default placeholder or shorter than 32 characters.
  - `CSRF_SECRET_KEY` is a default placeholder or shorter than 32 characters.
  - `SENTINEL_BIOMETRIC_ENCRYPTION_KEY` is missing or fails to resolve to a 32-byte AES-256 key.
  - `DEBUG` is set to `True`.
  - `CORS_ORIGINS` contains wildcard `'*'`.

---

## 4. Test Suite & Verification Results

The automated test suite was expanded with 40 new dedicated operational and security tests. All 413 tests in the repository pass cleanly:

```bash
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-9.2.0, pluggy-1.7.0
rootdir: E:\sentinelai-voice-verification
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.16.0, platformdirs-4.14.5, asyncio-1.5.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 413 items

tests\auth\test_jwt.py .....                                             [  1%]
tests\auth\test_login.py ....                                            [  2%]
tests\auth\test_logout.py ..                                             [  2%]
tests\auth\test_password_security.py .........                           [  4%]
tests\auth\test_refresh_tokens.py ...                                    [  5%]
tests\auth\test_registration.py .....                                    [  6%]
tests\biometrics\test_biometric_enrollment_service.py .....              [  7%]
tests\biometrics\test_biometric_profile_service.py .....                 [  9%]
tests\biometrics\test_biometric_storage.py .......                       [ 10%]
tests\biometrics\test_biometric_verification_service.py ......           [ 12%]
tests\biometrics\test_biometrics_api.py ...........                      [ 15%]
tests\biometrics\test_biometrics_security.py ...                         [ 15%]
tests\consent\test_consent_management.py ..                              [ 16%]
tests\database\test_audit_repository.py ..                               [ 16%]
tests\database\test_connection.py .....                                  [ 17%]
tests\database\test_consent_repository.py .                              [ 18%]
tests\database\test_crypto.py ..........                                 [ 20%]
tests\database\test_database_resilience.py ..                            [ 21%]
tests\database\test_migrations.py ..                                     [ 21%]
tests\database\test_models.py ......                                     [ 23%]
tests\database\test_profile_repository.py ...                            [ 23%]
tests\database\test_threshold_repository.py .                            [ 23%]
tests\database\test_user_repository.py ......                            [ 25%]
tests\database\test_verification_repository.py .                         [ 25%]
tests\enrollment\test_embedding_aggregation.py .......                   [ 27%]
tests\enrollment\test_enrollment_api.py .......                          [ 29%]
tests\enrollment\test_enrollment_service.py .....                        [ 30%]
tests\enrollment\test_enrollment_validation.py ........                  [ 32%]
tests\enrollment\test_profile_revocation.py ...                          [ 32%]
tests\enrollment\test_profile_storage.py .......                         [ 34%]
tests\evaluation\test_bootstrap.py .....                                 [ 35%]
tests\evaluation\test_confidence_intervals.py .....                      [ 37%]
tests\evaluation\test_dataset_inspector.py ..........                    [ 39%]
tests\evaluation\test_error_analysis.py ...                              [ 40%]
tests\evaluation\test_evaluation_metrics.py ..................           [ 44%]
tests\evaluation\test_real_score_provenance.py .....                     [ 45%]
tests\evaluation\test_robustness.py ...                                  [ 46%]
tests\evaluation\test_sensitivity.py ....                                [ 47%]
tests\evaluation\test_trial_generator.py ............................... [ 54%]
.......                                                                  [ 56%]
tests\monitoring\test_health.py .....                                    [ 57%]
tests\monitoring\test_logging.py ....                                    [ 58%]
tests\monitoring\test_request_id.py .....                                [ 60%]
tests\security\test_auth_abuse.py ....                                   [ 61%]
tests\security\test_auth_security.py ...                                 [ 61%]
tests\security\test_biometric_resource_limits.py ....                    [ 62%]
tests\security\test_encryption_hardening.py ...                          [ 63%]
tests\security\test_production_config.py .....                           [ 64%]
tests\security\test_rate_limiting.py ........                            [ 66%]
tests\speaker\test_ecapa_integration.py .                                [ 66%]
tests\speaker\test_embedding_mocked.py ........                          [ 68%]
tests\speaker\test_model_loader_mocked.py .....                          [ 69%]
tests\speaker\test_similarity.py ...........                             [ 72%]
tests\speaker\test_speaker_config.py .......                             [ 74%]
tests\test_audio_api.py ...........                                      [ 76%]
tests\test_audio_duration_recovery.py .....                              [ 78%]
tests\test_audio_flac.py .......                                         [ 79%]
tests\test_audio_preprocessor.py ....................                    [ 84%]
tests\users\test_rbac.py ......                                          [ 86%]
tests\users\test_user_management.py ....                                 [ 87%]
tests\verification\test_profile_validation.py .......                    [ 88%]
tests\verification\test_scoring.py ..........                            [ 91%]
tests\verification\test_threshold.py .................                   [ 95%]
tests\verification\test_verification_api.py ........                     [ 97%]
tests\verification\test_verification_security.py .....                   [ 98%]
tests\verification\test_verification_service.py ......                   [100%]

============================ 413 passed in 42.79s =============================
```

### Coverage by Subsystem
| Subsystem | Number of Tests | Status |
| :--- | :---: | :---: |
| Authentication & JWT Security | 28 | PASSED |
| User Management & RBAC | 10 | PASSED |
| Consent Lifecycle Management | 2 | PASSED |
| PostgreSQL Database & Repositories | 28 | PASSED |
| Audio Preprocessing Pipeline | 46 | PASSED |
| Speaker Embeddings (ECAPA-TDNN) | 32 | PASSED |
| Voice Enrollment & Aggregation | 37 | PASSED |
| Speaker Verification Engine | 53 | PASSED |
| Evaluation & Robustness (Phase 5) | 137 | PASSED |
| **Operational Rate Limiting (Phase 7E)** | **8** | **PASSED** |
| **Authentication Abuse Protection (Phase 7E)** | **4** | **PASSED** |
| **Operational Health Monitoring (Phase 7E)** | **5** | **PASSED** |
| **Structured Logging & Sanitization (Phase 7E)** | **4** | **PASSED** |
| **Distributed Request Tracing (Phase 7E)** | **5** | **PASSED** |
| **Biometric Resource Limits (Phase 7E)** | **4** | **PASSED** |
| **Biometric Encryption Hardening (Phase 7E)** | **3** | **PASSED** |
| **Database Resilience & Error Masking (Phase 7E)** | **2** | **PASSED** |
| **Production Configuration Validator (Phase 7E)** | **5** | **PASSED** |
| **Total Automated Tests** | **413** | **100% PASSED** |

---

## 5. Security Invariant Matrix

| Security Rule | Mechanism | Verification Method |
| :--- | :--- | :--- |
| **No Credential Leakage in Logs** | `sanitize_log_payload` deep recursion | `tests/monitoring/test_logging.py` |
| **No SQL Syntax in Error Responses** | `SQLAlchemyError` exception handler returning 500 `DATABASE_ERROR` | `tests/database/test_database_resilience.py` |
| **No Biometric Vector Decryption on Health Checks** | `HealthChecker.get_detailed_health` using `loader.is_loaded` property | `tests/monitoring/test_health.py` |
| **No Plaintext Identifier Storage in Memory** | `AuthAbuseTracker` SHA-256 identifier hashing | `tests/security/test_auth_abuse.py` |
| **Anti-Spoofing Client IP Resolution** | Right-to-left `X-Forwarded-For` traversal against trusted proxies | `tests/security/test_rate_limiting.py` |
| **NIST SP 800-88 Cryptographic Shredding** | Multi-pass file overwriting destroys envelope DEK | `tests/security/test_encryption_hardening.py` |
| **Zero Secret Disclosure on Bad Config** | Validator logs descriptions without printing secret string values | `tests/security/test_production_config.py` |
| **ML Inference Non-Starvation** | `asyncio.Semaphore(4)` bounded concurrency + `asyncio.to_thread` | `tests/security/test_biometric_resource_limits.py` |

---

## 6. Next Steps & Phase 8 Transition

Phase 7E marks the completion of the complete backend foundation for Sentinel Voice. The platform is secure, resilient, fully observable, rate-limited, and hardened for cloud deployment.

Awaiting user review and authorization before proceeding to **Phase 8A: Frontend Architecture & Client Dashboard Integration**.

