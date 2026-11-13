# Sentinel Voice — Repository Architecture & Directory Reorganization
**Document ID:** `DOC-P7-08`  
**Phase:** 7A (Standalone Application Architecture & System Design)  
**Status:** Approved Architecture Draft  

---

## 1. Audit of Current Repository Structure

The existing `sentinelai-voice-verification` repository is an independent research and engineering codebase that has successfully completed Phases 1 through 5E.

### 1.1 Existing Layout Inventory
```
sentinelai-voice-verification/
├── sentinelai/                     # Core Python modules
│   ├── audio/                      # Phase 1: Preprocessor, Validator, Metrics
│   ├── speaker/                    # Phase 2: ECAPA-TDNN Loader, Embedding, Similarity
│   ├── enrollment/                 # Phase 3: Aggregation, Storage, Schemas, Service, API
│   ├── verification/               # Phase 4: Scoring, Threshold, Audit, Service, API
│   ├── evaluation/                 # Phase 5: Inspector, Discovery, Scorer, Bootstrap, Visualizer
│   └── main.py                     # Initial FastAPI prototype application
├── scripts/                        # Standalone execution CLI scripts
│   ├── run_evaluation.py           # Phase 5C benchmark evaluation
│   ├── run_robustness_analysis.py  # Phase 5D statistical validation
│   └── generate_verification_trials.py # Phase 5B trial manifest generator
├── tests/                          # Automated Pytest suite (256 passing tests)
├── reports/                        # Evaluation reports, JSON metrics, publication figures
├── datasets/                       # Local benchmark datasets (gitignored)
├── outputs/                        # Cached .npz embeddings & trial manifests (gitignored)
├── pyproject.toml                  # Python package definition and dependencies
└── README.md                       # Project overview and research benchmark documentation
```

---

## 2. Target Production Repository Architecture

To scale Sentinel Voice into a professional, standalone SaaS application, the repository will be cleanly partitioned into a modern frontend client, an enterprise backend service layer, and database migration infrastructure, **while strictly preserving all existing Phase 1–5 research code and benchmark artifacts**:

```
sentinelai-voice-verification/
│
├── frontend/                       # NEXT.JS WEB CLIENT (Phase 7E)
│   ├── app/                        # Next.js 14 App Router pages
│   │   ├── (auth)/                 # Login, Register, Forgot Password
│   │   ├── (dashboard)/            # Protected Dashboard Layout
│   │   │   ├── page.tsx            # Main Overview Dashboard
│   │   │   ├── enrollment/         # Voice Enrollment Studio
│   │   │   ├── verification/       # 1:1 Voice Verification Console
│   │   │   ├── profiles/           # Voice Profile Management
│   │   │   ├── history/            # Verification History & Audit Explorer
│   │   │   ├── analytics/          # Dual-Layer Analytics (Live + Benchmarks)
│   │   │   ├── users/              # Administrative User Management
│   │   │   ├── api-keys/           # Developer API Keys & Usage Quota
│   │   │   └── settings/           # Account & Biometric Policy Settings
│   │   ├── layout.tsx              # Root HTML Layout
│   │   └── globals.css             # Tailwind CSS directives
│   ├── components/                 # Reusable UI Components
│   │   ├── ui/                     # Buttons, Cards, Inputs, Modals, Tables, Badges
│   │   ├── audio/                  # Microphone Recorder, Audio Waveform Visualizer
│   │   ├── charts/                 # Recharts Trend Lines, Score Histograms
│   │   └── layout/                 # Sidebar, Navigation Bar, User Menu
│   ├── services/                   # Client API Communication SDK (Axios/Fetch)
│   ├── hooks/                      # Custom React Hooks (useAudioRecorder, useAuth)
│   ├── types/                      # TypeScript Interface Definitions
│   ├── package.json                # Frontend Node.js Dependencies
│   ├── tsconfig.json               # TypeScript Configuration
│   └── tailwind.config.js          # Tailwind Design Tokens
│
├── sentinelai/                     # BACKEND PYTHON APPLICATION
│   ├── api/                        # REST API Routing Layer (Phase 7B/7D)
│   │   ├── v1/
│   │   │   ├── auth.py             # Login, Register, Token Refresh
│   │   │   ├── users.py            # User Administration & Profile
│   │   │   ├── enrollment.py       # Multi-Utterance Voice Enrollment
│   │   │   ├── verification.py     # 1:1 Speaker Verification
│   │   │   ├── analytics.py        # Live Telemetry & Historical Benchmarks
│   │   │   └── api_keys.py         # Developer API Key Lifecycle
│   │   └── deps.py                 # Dependency Injection Providers (DB, Current User)
│   ├── auth/                       # Security & Identity Modules (Phase 7C)
│   │   ├── security.py             # Argon2id password hashing, JWT encoder/decoder
│   │   ├── csrf.py                 # Double-submit CSRF token validation
│   │   ├── crypto.py               # AES-256-GCM vector payload encryption
│   │   ├── rbac.py                 # Role & Permission Verification Guards
│   │   └── api_keys.py             # API Key Generation & Hashing
│   ├── database/                   # Relational Persistence (Phase 7B)
│   │   ├── connection.py           # Async SQLAlchemy Engine & Session Factory
│   │   ├── base.py                 # Declarative Base Model
│   │   ├── models/                 # SQLAlchemy 2.0 ORM Models
│   │   │   ├── user.py             # User, Role, UserRole, RefreshToken
│   │   │   ├── profile.py          # VoiceProfile, EnrollmentRecord, ConsentRecord
│   │   │   ├── verification.py     # VerificationEvent
│   │   │   ├── threshold.py        # ThresholdConfiguration
│   │   │   └── audit.py            # AuditLog, ApiCredential
│   │   └── repositories/           # Repository Pattern Data Access Classes
│   ├── services/                   # Domain Business Logic Layer (Phase 7B/7D)
│   │   ├── auth_service.py         # Authentication & Session Workflows
│   │   ├── user_service.py         # User Management & RBAC Administration
│   │   ├── threshold_service.py    # Configurable Threshold Management & Provable Metadata
│   │   ├── enrollment_service.py   # Voice Enrollment Orchestrator
│   │   ├── verification_service.py # 1:1 Verification Orchestrator
│   │   └── analytics_service.py    # Operational Statistics Aggregator
│   ├── audio/                      # [PRESERVED Phase 1] Preprocessor & Validator
│   ├── speaker/                    # [PRESERVED Phase 2] ECAPA-TDNN Model & Embedding
│   ├── enrollment/                 # [PRESERVED Phase 3] Centroid Aggregation & Local Storage
│   ├── verification/               # [PRESERVED Phase 4] Threshold Logic & Cosine Scoring
│   ├── evaluation/                 # [PRESERVED Phase 5] Inspector, Scorer, Bootstrap, Visualizer
│   └── main.py                     # Production FastAPI Application Entry Point
│
├── migrations/                     # ALEMBIC DATABASE MIGRATIONS (Phase 7B)
│   ├── versions/                   # Migration Scripts (0001_initial_schema.py)
│   ├── env.py                      # Alembic Environment Config
│   └── script.py.mako              # Migration Template
│
├── tests/                          # COMPREHENSIVE AUTOMATED TEST SUITE
│   ├── audio/                      # Audio preprocessing unit tests
│   ├── speaker/                    # ECAPA-TDNN model tests
│   ├── enrollment/                 # Enrollment aggregation & storage tests
│   ├── verification/               # Verification scoring & threshold tests
│   ├── evaluation/                 # Phase 5 benchmark & bootstrap tests
│   └── api/                        # [NEW Phase 7] API Endpoint Integration Tests
│
├── docs/                           # ARCHITECTURAL DOCUMENTATION
│   └── phase-7/                    # Standalone SaaS Architecture Specifications
├── scripts/                        # Evaluation, maintenance, and setup scripts
├── reports/                        # Historical research benchmarks (Phase 5E)
├── pyproject.toml                  # Python Dependencies & Metadata
├── docker-compose.yml              # Local Development Infrastructure (Postgres, Web, API)
└── README.md                       # Platform Documentation & Research Benchmarks
```

---

## 3. Safe Migration Strategy: Zero Regressions

To prevent any breaking changes to the 256 existing passing unit tests and scientific scripts:

1. **Additive Architecture:** New features (database models, auth routers, frontend code) are created in new directories (`sentinelai/database/`, `sentinelai/auth/`, `sentinelai/api/v1/`, `frontend/`).
2. **Backward Compatibility Aliasing:** Existing endpoints in `sentinelai/enrollment/api.py` and `sentinelai/verification/api.py` remain functional as legacy routes while forwarding requests to the unified service layer.
3. **Preservation of Evaluation Artifacts:** The `reports/` directory and historical JSON metrics remain completely untouched.
4. **Independent Dependency Management:** The Next.js frontend maintains its own isolated `package.json`, completely independent from Python's `pyproject.toml`.

