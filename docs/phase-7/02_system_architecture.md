# Sentinel Voice — System Architecture & Topology
**Document ID:** `DOC-P7-02`  
**Phase:** 7A (Standalone Application Architecture & System Design)  
**Status:** Approved Architecture Draft  

---

## 1. High-Level Architecture Diagram

Sentinel Voice is structured as a modular, three-tier enterprise SaaS application. The frontend and backend communicate exclusively over strict, authenticated RESTful APIs over HTTPS/JSON.

```mermaid
graph TD
    subgraph Client_Tier ["Client Tier (Browser / Mobile / API Client)"]
        Browser["Modern Web Browser (Chrome, Safari, Edge)"]
        APIClient["External Developer / Enterprise Client"]
    end

    subgraph Presentation_Tier ["Presentation Tier (Next.js 14 App Router)"]
        NextApp["Next.js Application Server (SSR & Static Assets)"]
        ReactUI["Responsive React 18 Components (Tailwind CSS)"]
        ClientState["Client Session & Auth Context"]
    end

    subgraph Application_Tier ["Application Tier (FastAPI Engine)"]
        APIGateway["FastAPI HTTP / REST Router (OpenAPI 3.1)"]
        AuthMiddleware["JWT Authentication & RBAC Middleware"]
        RateLimiter["Redis / In-Memory Rate Limiting"]
        
        subgraph Business_Services ["Core Domain Services"]
            UserService["User & Identity Service"]
            EnrollService["Enrollment Orchestration Service"]
            VerifyService["1:1 Verification Service"]
            AuditService["Privacy-Safe Audit & Analytics Service"]
        end
    end

    subgraph AI_Inference_Tier ["AI & Feature Extraction Engine (Python / PyTorch)"]
        AudioPreprocessor["Audio Validation & Resampling (16 kHz Mono)"]
        ModelSingleton["ECAPAModelLoader (Thread-Safe Lazy Singleton)"]
        SpeechBrainECAPA["SpeechBrain ECAPA-TDNN Backbone (192D)"]
        CentroidAggregator["L2-Normalized Centroid Aggregator"]
        CosineEngine["Directional Cosine Similarity Engine"]
    end

    subgraph Data_Tier ["Data & Persistence Tier"]
        PostgresDB[("PostgreSQL 15+ (Relational State & Audit Logs)")]
        BiometricStore[("Secure Encrypted Biometric Storage (.npz / AES-256)")]
        TempAudio["Ephemeral Memory Buffer (Audio Temp Cache)"]
    end

    %% Connections
    Browser --> NextApp
    NextApp --> ReactUI
    ReactUI -->|HTTPS / JSON / Multipart| APIGateway
    APIClient -->|API Key / Bearer JWT| APIGateway

    APIGateway --> AuthMiddleware
    AuthMiddleware --> RateLimiter
    RateLimiter --> UserService
    RateLimiter --> EnrollService
    RateLimiter --> VerifyService
    RateLimiter --> AuditService

    EnrollService --> AudioPreprocessor
    VerifyService --> AudioPreprocessor
    AudioPreprocessor --> TempAudio
    TempAudio --> ModelSingleton
    ModelSingleton --> SpeechBrainECAPA
    SpeechBrainECAPA --> CentroidAggregator
    SpeechBrainECAPA --> CosineEngine

    UserService --> PostgresDB
    AuditService --> PostgresDB
    EnrollService --> PostgresDB
    EnrollService --> BiometricStore
    VerifyService --> PostgresDB
    VerifyService --> BiometricStore
```

---

## 2. Core Architectural Principles

### 2.1 Complete AI Inference Independence
The AI Inference Engine (`sentinelai.speaker`, `sentinelai.audio`) remains completely isolated from the web presentation layer:
- The Next.js frontend has **zero direct dependency** on PyTorch, SpeechBrain, or audio DSP code.
- Frontend components communicate exclusively via HTTP multipart form payloads and structured JSON responses.
- The AI layer accepts generic standard streams or byte buffers (`bytes` / `io.BytesIO`) and produces plain Python/NumPy arrays without web framework couplings.

### 2.2 Singleton Model Lifecycle Management
To maximize performance and prevent out-of-memory (OOM) crashes on resource-constrained systems (e.g. 8GB RAM host environments):
- Pretrained weights for `speechbrain/spkrec-ecapa-voxceleb` are loaded **strictly once** via `ECAPAModelLoader`.
- The model loader employs a thread-safe double-checked locking pattern (`threading.Lock()`).
- Workers and threads share the single in-memory instance for evaluation and inference.
- GPU acceleration (`cuda:0`) is automatically utilized if available; otherwise, it defaults gracefully to multi-threaded CPU inference.

### 2.3 Strict Separation of Biometric and Ordinary User Data
To align with biometric privacy principles (such as GDPR Article 9, CCPA, and Illinois BIPA):
- Relational user profile data (email, name, role, hashed passwords) is stored in standard PostgreSQL tables.
- Biometric embeddings (192-dimensional floating-point vectors) are **never stored in plain relational columns**.
- Embeddings are persisted in dedicated, encrypted binary storage (AES-256-GCM encrypted NumPy `.npz` containers with atomic filesystem writes and restricted file permissions `0600`).
- **Cryptographic Key Separation:** The master vector encryption key (`SENTINEL_BIOMETRIC_ENCRYPTION_KEY`) is stored strictly in isolated environment variables or an external KMS, completely decoupled from the PostgreSQL database.
- The database stores only foreign references, vector hashes (SHA-256), dimension metadata, and non-sensitive timestamps.

### 2.4 Ephemerality of Raw Voice Audio & In-Memory Ingestion
Raw audio recordings submitted for enrollment or verification are subject to strict data minimization:
1. Audio is held in volatile memory buffers (`io.BytesIO`) during container validation, decoding, and preprocessing.
2. Temporary disk files are avoided entirely. In the rare event a temporary disk scratch is required by a legacy library, it is written to a secure volatile RAM disk (`tmpfs`) and cryptographically zeroed immediately after tensor extraction.
3. Once the 192-dimensional embedding vector is extracted, the temporary audio memory buffer is overwritten and garbage collected.
4. Raw waveforms are **never permanently stored**, and neither audio bytes nor biometric vectors are ever logged in application traces.

### 2.5 Configurable Decision Threshold Management
The decision threshold is **never hardcoded** in application logic:
- While $\theta^* = 0.4059$ represents the historical Phase 5E scientific baseline (calibrated on LibriSpeech `dev-clean`), production systems require operational adaptability.
- The platform implements dynamic threshold management loaded from the `threshold_configurations` database entity or environment configuration.
- Each threshold record encapsulates:
  - Model identifier (e.g. `speechbrain/spkrec-ecapa-voxceleb`).
  - Active threshold value ($\theta$).
  - Calibration dataset and criterion (e.g. `equal_error_rate`).
  - Calibration metadata and historical provenance.
  - Active status toggle with administrative auditing.
- Historical Phase 5E research benchmark metrics remain immutable and preserved for research provenance.

### 2.6 Offloaded Asynchronous Concurrency
PyTorch tensor math and model forward passes are computationally intensive. To keep the ASGI async event loop responsive and maintain sub-second response times:
- All audio decoding and ECAPA embedding forward passes are offloaded from the event loop using `asyncio.to_thread` / AnyIO worker pools.
- The system is fully tested and optimized for CPU-only environments (bounded serial processing, memory footprint $< 1.5\text{ GB}$).

---

## 3. End-to-End Runtime Data Flows

### 3.1 Voice Enrollment Workflow
```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant FE as Next.js Web App
    participant API as FastAPI Gateway
    participant Svc as Enrollment Service
    participant Pre as Audio Preprocessor
    participant AI as ECAPA-TDNN Model
    participant DB as PostgreSQL
    participant Bio as Secure Vector Storage

    User->>FE: Records/Uploads 3 Voice Samples & Checks Consent
    FE->>API: POST /api/v1/enrollment (multipart files + user_id + consent)
    API->>Svc: Validate Auth Token & Input Constraints
    Svc->>DB: Check User Status & Existing Active Profile
    Svc->>DB: Record Biometric Consent Event
    loop For each of K=3 Audio Samples
        Svc->>Pre: Validate Header (WAV/FLAC), SNR, Duration (1.0s–60.0s)
        Pre-->>Svc: Mono 16 kHz Float32 Tensor
        Svc->>AI: Extract 192D Embedding Vector e_k
        AI-->>Svc: L2-Normalized Embedding Vector
    end
    Svc->>Svc: Aggregate Centroid: e_ref = Normalize(Mean(e_1, e_2, e_3))
    Svc->>Bio: Atomically Write Profile Vectors (.npz, permissions 0600)
    Svc->>DB: Insert voice_profile & enrollment_records Metadata
    Svc-->>API: EnrollmentResponse (profile_id, status=ACTIVE, no raw vectors)
    API-->>FE: 201 Created JSON
    FE-->>User: Display Enrollment Success Confirmation
```

### 3.2 1:1 Voice Verification Workflow
```mermaid
sequenceDiagram
    autonumber
    actor Claimant as Voice Claimant
    participant FE as Next.js Web App
    participant API as FastAPI Gateway
    participant Svc as Verification Service
    participant Pre as Audio Preprocessor
    participant AI as ECAPA-TDNN Model
    participant Bio as Secure Vector Storage
    participant DB as PostgreSQL

    Claimant->>FE: Submits Audio Probe & Claimed Identity
    FE->>API: POST /api/v1/verification (audio probe + claimed_user_id)
    API->>Svc: Verify Rate Limit & Session Authenticity
    Svc->>DB: Fetch Active Profile ID for Claimed User
    alt Profile Not Found or Revoked
        Svc-->>API: 404 / 403 Profile Ineligible
        API-->>FE: Error Response
    else Profile Active
        Svc->>Bio: Load Reference Vector e_ref
        Svc->>Pre: Validate Audio & Resample to 16 kHz Mono
        Pre-->>Svc: Normalized Probe Tensor
        Svc->>AI: Extract 192D Probe Vector e_probe
        Svc->>Svc: Compute Cosine Similarity: s = dot(e_ref, e_probe)
        Svc->>Svc: Compare against Calibrated Threshold: s >= θ* (0.4059)
        Svc->>DB: Insert immutable verification_events record
        Svc-->>API: VerificationResponse (MATCH/NO_MATCH, score, latency)
        API-->>FE: 200 OK JSON
        FE-->>Claimant: Visual Decision Indicator (Green/Red Badge)
    end
```

---

## 4. Extension Hooks for Future Phases (Phases 8–10)

Although anti-spoofing, intent analysis, and security fusion are strictly postponed, the architecture defines concrete interface slots to ensure seamless future adoption without refactoring core services:

```python
# Sentinel Voice Modular Verification Pipeline (Architecture Interface)
class VerificationPipelineInterface:
    async def process_verification(self, audio_tensor, reference_profile):
        # Current Phase 7: Biometric Verification
        biometric_score = compute_cosine_similarity(
            extract_ecapa(audio_tensor), reference_profile.embedding
        )
        
        # Future Extension Slot (Phase 8): Presentation Attack Detection
        # pad_score = await pad_engine.predict_bona_fide(audio_tensor)
        pad_score = None 
        
        # Future Extension Slot (Phase 9): Malicious Intent Detection
        # intent_score = await intent_engine.analyze(audio_tensor)
        intent_score = None
        
        # Future Extension Slot (Phase 10): Three-Level Fusion Decision
        # decision = fusion_engine.fuse(biometric_score, pad_score, intent_score)
        decision = "MATCH" if biometric_score >= CALIBRATED_THRESHOLD else "NO_MATCH"
        
        return VerificationResult(
            decision=decision,
            similarity_score=biometric_score,
            pad_score=pad_score,
            intent_score=intent_score
        )
```

