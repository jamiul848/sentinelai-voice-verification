# Sentinel Voice — Database Architecture & Implementation Specification
**Document ID:** `DOC-P7-10`  
**Phase:** 7B (PostgreSQL Database, SQLAlchemy ORM, Alembic Migrations & Backend Foundation)  
**Status:** Implemented & Verified  
**Date:** 2026-11-13  
**Repository:** `https://github.com/jamiul848/sentinelai-voice-verification`  

---

## 1. Executive Overview

This document details the production-ready PostgreSQL persistence tier, SQLAlchemy 2.0 async ORM models, Alembic migration pipeline, and repository abstraction layer implemented for **Sentinel Voice** in Phase 7B.

The database tier is designed to meet strict security and privacy standards (GDPR Article 9, Illinois BIPA) while maintaining complete backward compatibility with the existing speaker recognition research modules (`sentinelai/audio`, `sentinelai/speaker`, `sentinelai/enrollment`, `sentinelai/verification`, `sentinelai/evaluation`).

---

## 2. Technology Stack & Dependencies

| Layer | Component | Version | Role |
| :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.12+ | Core runtime environment |
| **Database** | PostgreSQL | 15+ (tested on PG 18) | Persistent relational store |
| **ORM** | SQLAlchemy | 2.0+ (asyncio) | Declarative entity modeling & async query compilation |
| **Driver** | AsyncPG | 0.28+ | High-throughput asynchronous PostgreSQL DBAPI |
| **Migrations** | Alembic | 1.12+ | Asynchronous database schema version control |
| **Configuration** | Pydantic Settings | 2.0+ | Type-safe environment variable parsing |
| **Cryptography** | Cryptography | 41.0+ | AES-256-GCM vector encryption at rest |
| **Test Runner** | Pytest & pytest-asyncio | 8.x / 1.x | Async test suite orchestration |
| **Test Driver** | Aiosqlite | 0.19+ | Isolated in-memory async database driver for unit tests |

---

## 3. Database Architecture & ER Diagram

```mermaid
erDiagram
    users ||--o{ user_roles : "assigned"
    roles ||--o{ user_roles : "grants"
    users ||--o{ refresh_tokens : "owns"
    users ||--o{ api_credentials : "owns"
    users ||--o{ consent_records : "authorizes"
    users ||--o{ voice_profiles : "owns"
    voice_profiles ||--o{ enrollment_records : "aggregated_from"
    voice_profiles ||--o{ verification_events : "evaluated_against"
    users ||--o{ verification_events : "attempts"
    users ||--o{ audit_logs : "triggers"

    users {
        uuid id PK
        varchar email UK
        varchar hashed_password
        varchar full_name
        boolean is_active
        boolean is_verified
        timestamp created_at
        timestamp updated_at
    }

    roles {
        uuid id PK
        varchar name UK
        text description
        json permissions
        timestamp created_at
    }

    user_roles {
        uuid id PK
        uuid user_id FK
        uuid role_id FK
        timestamp assigned_at
    }

    refresh_tokens {
        uuid id PK
        uuid user_id FK
        varchar token_hash UK
        timestamp expires_at
        boolean is_revoked
        timestamp created_at
        timestamp revoked_at
    }

    api_credentials {
        uuid id PK
        uuid user_id FK
        varchar name
        varchar key_prefix
        varchar key_hash UK
        json scopes
        timestamp last_used_at
        boolean is_active
        timestamp created_at
        timestamp revoked_at
    }

    consent_records {
        uuid id PK
        uuid user_id FK
        varchar consent_type
        boolean consent_granted
        varchar consent_version
        varchar ip_address
        timestamp created_at
    }

    voice_profiles {
        uuid id PK
        uuid user_id FK
        varchar status
        integer sample_count
        numeric mean_pairwise_similarity
        varchar model_identifier
        varchar embedding_storage_path
        varchar embedding_sha256
        timestamp created_at
        timestamp updated_at
        timestamp revoked_at
    }

    enrollment_records {
        uuid id PK
        uuid profile_id FK
        numeric duration_sec
        numeric rms_energy
        numeric peak_amplitude
        numeric snr_db
        varchar audio_format
        timestamp created_at
    }

    verification_events {
        uuid id PK
        uuid user_id FK
        uuid profile_id FK
        varchar decision
        numeric similarity_score
        numeric applied_threshold
        boolean is_match
        numeric processing_time_ms
        varchar client_ip
        timestamp created_at
    }

    audit_logs {
        uuid id PK
        uuid actor_user_id FK
        varchar action
        varchar resource_type
        varchar resource_id
        json changes
        timestamp created_at
    }
```

---

## 4. The Ten Core Relational Entities

### 4.1 `users`
- **Primary Key:** `id` (`UUID`, generated via CSPRNG `uuid.uuid4`).
- **Normalized Email:** Lowercased and whitespace-trimmed via `@validates("email")` validator before insertion.
- **Constraints:** `UNIQUE (email)`.
- **Indexes:** `idx_users_email` (unique B-tree), `idx_users_is_active`, `idx_users_email_lower`.

### 4.2 `roles`
- **Primary Key:** `id` (`UUID`).
- **Semantic Roles:** `SUPER_ADMIN`, `ADMIN`, `ANALYST`, `END_USER`.
- **Permissions:** Stored as structured JSON / JSONB array.
- **Constraints:** `UNIQUE (name)`.

### 4.3 `user_roles`
- **Primary Key:** `id` (`UUID`).
- **Foreign Keys:** `user_id -> users.id (CASCADE)`, `role_id -> roles.id (CASCADE)`.
- **Constraints:** `UNIQUE (user_id, role_id)` preventing duplicate role assignments.

### 4.4 `refresh_tokens`
- **Primary Key:** `id` (`UUID`).
- **Security Rule:** Never stores raw refresh tokens; stores SHA-256 hex digest (`token_hash`).
- **Lifecycle:** Tracks `is_revoked`, `expires_at`, and `revoked_at`.

### 4.5 `api_credentials`
- **Primary Key:** `id` (`UUID`).
- **Security Rule:** Never stores raw API key secrets; retains visible prefix (e.g. `sv_live_...`) and SHA-256 hash (`key_hash`).
- **Scopes:** Scoped permissions (e.g. `["verify"]`).

### 4.6 `consent_records`
- **Primary Key:** `id` (`UUID`).
- **Audit Rule:** Immutable; chronological history is preserved without overwriting prior records.
- **Constraints:** `CHECK (consent_granted = 1 OR consent_granted = TRUE)`.

### 4.7 `voice_profiles`
- **Primary Key:** `id` (`UUID`).
- **Lifecycle Statuses:** `ACTIVE` or `REVOKED`.
- **Biometric Separation Invariant:** Raw 192D float arrays are strictly prohibited from database columns; stores only `embedding_storage_path` (pointing to isolated AES-256-GCM container) and `embedding_sha256`.
- **Constraints:** `CHECK (sample_count >= 3)`.

### 4.8 `enrollment_records`
- **Primary Key:** `id` (`UUID`).
- **Zero Audio Invariant:** Stores only acoustic metadata (`duration_sec`, `rms_energy`, `peak_amplitude`, `snr_db`, `audio_format`). Raw voice waveforms are never stored.
- **Constraints:** `CHECK (duration_sec >= 1.0 AND duration_sec <= 60.0)`.

### 4.9 `verification_events`
- **Primary Key:** `id` (`UUID`).
- **Ledger Invariant:** Append-only transaction log of 1:1 speaker verifications (`user_id`, `profile_id`, `decision: MATCH/NO_MATCH`, `similarity_score`, `applied_threshold`, `is_match`, `processing_time_ms`, `client_ip`).

### 4.10 `audit_logs`
- **Primary Key:** `id` (`UUID`).
- **Ledger Invariant:** Append-only security and administrative event ledger tracking `actor_user_id`, `action`, `resource_type`, `resource_id`, and `changes` (omitting secrets and vectors).

---

## 5. Repository Architecture

Repositories are decoupled from business logic and encapsulated under `sentinelai/database/repositories/`:

```
sentinelai/database/repositories/
├── base.py                   # Generic BaseRepository[T] with get_by_id, list_all, count, add
├── user_repository.py         # UserRepository: create_user, get_by_id, get_by_email, list_users, update_user, deactivate_user, roles, tokens
├── profile_repository.py      # ProfileRepository: create_profile, get_profile_by_id, get_active_profile_by_user, list_profiles, update_profile_status, revoke_profile
├── audit_repository.py        # AuditRepository: create_audit_event, get_audit_history, list_resource_events
├── consent_repository.py      # ConsentRepository: create_consent_record, get_user_consent_history, get_latest_consent
└── verification_repository.py # VerificationRepository: create_verification_event, get_verification_by_id, get_user_verification_history
```

---

## 6. Setup, Configuration & Migration Commands

### 6.1 Environment Configuration (`.env`)
Create `.env` using `.env.example` as a template:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel_secure_password@localhost:5432/sentinel_voice
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false

# Biometric Vector Encryption Key (32-byte Base64 key)
SENTINEL_BIOMETRIC_ENCRYPTION_KEY=
```

### 6.2 PostgreSQL Database Initialization
Connect to your local PostgreSQL server and create the database user and database:

```sql
CREATE USER sentinel WITH PASSWORD 'sentinel_secure_password';
CREATE DATABASE sentinel_voice OWNER sentinel;
GRANT ALL PRIVILEGES ON DATABASE sentinel_voice TO sentinel;
```

### 6.3 Alembic Migration Execution
Run migrations using Alembic:

```powershell
# Upgrade to head revision (applies 0001_initial_schema.py)
alembic upgrade head

# Inspect current revision status
alembic current

# View migration history
alembic history --verbose

# Roll back by one revision
alembic downgrade -1

# Generate SQL without applying (offline preview)
alembic upgrade head --sql
```

---

## 7. Test Suite Execution & Results

### Running Unit & Repository Tests
```powershell
# Run all database-specific tests (connection, models, repositories, crypto, migrations)
pytest tests/database/ -v

# Run the entire test suite (research engine + database tier)
pytest
```

### Verified Test Results
- **Database test suite:** `36 passed in 9.20s` (100% pass rate).
- **Full repository test suite:** `292 passed in 72.17s` (256 existing research tests + 36 new database tests = 0 regressions).

