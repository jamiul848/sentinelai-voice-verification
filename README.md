# SentinelAI – Autonomous Voice Verification Platform

SentinelAI Voice Verification research module for speaker identity verification, anti-spoofing, and voice defense pipelines.

---

## 1. Overview & Architecture

SentinelAI provides an independent, modular speaker recognition and voice verification software pipeline. It operates in structured research phases:

- **Phase 1 (Complete):** Audio Preprocessing, Header & Numeric Validation, Resampling to 16 kHz Mono, Acoustic Metrics.
- **Phase 2 (Complete):** Pretrained ECAPA-TDNN Integration, Fixed-Dimensional Speaker Embedding Extraction, L2 Normalization, and Directional Cosine Similarity.
- **Phase 3 (Complete):** Multi-Utterance Voice Enrollment, Reference Profile Aggregation, Secure Profile Storage, and Profile Revocation.
- **Phase 4 (Complete):** 1:1 Speaker Verification Engine, Configurable Decision Thresholding, Privacy-Preserving Audit Logging, and Verification API.
- **Phase 5 (Upcoming):** Presentation Attack Detection (PAD) and Voice Anti-Spoofing Defense (Deepfake and physical replay detection).

```
sentinelai/
├── __init__.py
├── main.py                     # FastAPI application entry point (app = create_app())
├── audio/                      # Audio Preprocessing Module (Phase 1)
│   ├── __init__.py             # Public API exports
│   ├── api.py                  # Audio APIRouter (/audio/preprocess)
│   ├── cli.py                  # Command-line interface
│   ├── config.py               # AudioPreprocessingConfig (Pydantic model)
│   ├── exceptions.py           # Domain exception hierarchy (SentinelAudioError)
│   ├── metrics.py              # RMS energy, peak amplitude, dBFS calculations
│   ├── preprocessor.py         # AudioPreprocessor & AudioPreprocessingResult
│   └── validator.py            # Header, numeric, and duration validation logic
├── speaker/                    # Speaker Recognition Module (Phase 2)
│   ├── __init__.py             # Clean module exports
│   ├── config.py               # SpeakerConfig (Pydantic model: device, model_source, cache)
│   ├── exceptions.py           # Speaker domain exceptions (ModelLoadError, InvalidEmbeddingError)
│   ├── model.py                # ECAPAModelLoader (lazy, thread-safe model caching)
│   ├── embedding.py            # SpeakerEmbeddingExtractor & SpeakerEmbeddingResult
│   └── similarity.py           # Directional Cosine Similarity Engine
├── enrollment/                 # Voice Enrollment & Profile Management (Phase 3)
│   ├── __init__.py             # Clean module exports
│   ├── config.py               # EnrollmentConfig (min/max recordings, storage paths, consent)
│   ├── exceptions.py           # Enrollment domain exceptions (ConsentError, StorageError, etc.)
│   ├── schemas.py              # Pydantic schemas (SpeakerProfile, SpeakerProfilePublic, responses)
│   ├── aggregation.py          # Reference embedding aggregation & consistency evaluation
│   ├── storage.py              # Secure profile storage backend (JSON metadata + atomic .npz)
│   ├── service.py              # EnrollmentService orchestrator
│   └── api.py                  # Enrollment APIRouter (/enrollment/*)
└── verification/               # 1:1 Speaker Verification Engine (Phase 4)
    ├── __init__.py             # Clean module exports
    ├── config.py               # VerificationConfig (threshold, exposure toggle, audit paths)
    ├── exceptions.py           # Verification domain exceptions (VerificationError, etc.)
    ├── schemas.py              # VerificationResponse, VerificationHealthResponse, VerificationStatus
    ├── scoring.py              # Cosine similarity scoring with clipping & dimension checks
    ├── threshold.py            # VerificationThreshold manager with version tracking & bounds
    ├── audit.py                # Append-only privacy-safe audit logging (JSON lines)
    ├── service.py              # SpeakerVerificationService orchestrator
    └── api.py                  # Verification APIRouter (/verification/*)
scripts/
├── run_preprocessing_demo.py   # Phase 1 standalone preprocessing runner
├── run_speaker_embedding_demo.py # Phase 2 standalone ECAPA-TDNN embedding runner
├── run_enrollment_demo.py      # Phase 3 standalone voice enrollment & revocation runner
└── run_verification_demo.py    # Phase 4 standalone speaker verification trial runner
notebooks/
└── ecapa_embedding_demo.ipynb  # Interactive Google Colab & local Jupyter demonstration
tests/
├── conftest.py                 # Audio test fixtures (synthetic mathematical tones)
├── test_audio_api.py           # FastAPI application and endpoint tests
├── test_audio_preprocessor.py  # Audio preprocessing unit tests
├── speaker/                    # Speaker module test suite (Phase 2)
│   ├── __init__.py
│   ├── conftest.py             # Speaker fixtures & mock model classes
│   ├── test_speaker_config.py  # Configuration & device validation tests
│   ├── test_similarity.py      # Cosine similarity mathematical & edge case tests
│   ├── test_model_loader_mocked.py # Fast unit tests for model loader caching
│   ├── test_embedding_mocked.py# Fast unit tests for embedding extractor
│   └── test_ecapa_integration.py # Real live pretrained ECAPA-TDNN inference test
├── enrollment/                 # Enrollment module test suite (Phase 3)
│   ├── __init__.py
│   ├── conftest.py             # Enrollment fixtures, mock extractors, synthetic audio
│   ├── test_enrollment_validation.py # Input validation, consent & recording limits
│   ├── test_embedding_aggregation.py # Mathematical mean aggregation & consistency
│   ├── test_profile_storage.py # Storage, persistence, and schema safety tests
│   ├── test_profile_revocation.py # Revocation & biometric vector purging tests
│   ├── test_enrollment_service.py # Core service lifecycle (enroll, reenroll, status)
│   └── test_enrollment_api.py  # REST API integration & error handling tests
└── verification/               # Speaker verification test suite (Phase 4)
    ├── __init__.py
    ├── conftest.py             # Verification fixtures, test profiles, client fixtures
    ├── test_scoring.py         # Cosine scoring, dimension congruence, zero-norm guardrails
    ├── test_threshold.py       # Threshold bounds, evaluation rules, version tracking
    ├── test_profile_validation.py # Active profile lookup, revoked/missing/corrupted handling
    ├── test_verification_service.py # Match/No-Match workflows, latency, score masking
    ├── test_verification_api.py # FastAPI verification routes, upload limits, health checks
    └── test_verification_security.py # Privacy-leak prevention, audit sanitization, injection rejection
```

---

## 2. Core Security Distinctions

To maintain scientific rigor and clear boundaries across security domains:

| Component | Responsibility | Question Answered | Phase |
| :--- | :--- | :--- | :--- |
| **Voice Enrollment** | Multi-utterance acoustic template creation & secure storage | *"How do we capture and model an authorized reference identity?"* | Phase 3 (Done) |
| **Speaker Verification** | 1:1 acoustic similarity evaluation against a decision threshold | *"Does this candidate recording match the claimed identity's profile?"* | Phase 4 (Done) |
| **Voice Anti-Spoofing (PAD)** | Presentation attack detection (replay, synthesis, deepfakes) | *"Is this voice genuine, live human speech or an artificial artifact?"* | Phase 5 (Upcoming) |

> [!IMPORTANT]
> **Speaker Verification alone is NOT a complete authentication system.**
> A matching voice recording can still be a physical acoustic replay, a voice conversion sample, or a text-to-speech deepfake. Production deployment strictly requires integration with Phase 5 Presentation Attack Detection (PAD), session authorization tokens, and replay defense.

---

## 3. Speaker Verification Engine (Phase 4)

### Objective
The Speaker Verification Engine performs 1:1 identity verification:
> *"Does this newly submitted voice recording belong to the speaker whose voice profile is already enrolled?"*

### Pipeline Workflow
```
[Claimant Identity (user_id / profile_id)] + [Claimant Audio (WAV)]
                         │
                         ▼
             [Input Validation & Size Check]
                         │
                         ▼
        [Active Enrolled Profile Retrieval] ──> (Reject if NOT_FOUND or REVOKED)
                         │
                         ▼
          [Candidate Audio Preprocessing]  ──> (Validate 16kHz Mono, RMS, Duration)
                         │
                         ▼
       [ECAPA-TDNN Feature Extraction]    ──> (Extract 192-dim Unit Vector)
                         │
                         ▼
       [Directional Cosine Similarity]    ──> (Compute score in [-1.0, 1.0])
                         │
                         ▼
         [Threshold Comparison: score >= θ]
                         ├─── (True)  ──> MATCH    (verified=True)
                         └─── (False) ──> NO_MATCH (verified=False)
                         │
                         ▼
        [Privacy-Preserving Audit Event]   ──> (Append to verification_audit.jsonl)
                         │
                         ▼
         [Safe Public VerificationResponse] (Biometrics strictly withheld)
```

### Mathematical Scoring & Score Interpretation
Given reference vector $\mathbf{e}_{\text{ref}}$ and claimant vector $\mathbf{e}_{\text{claimant}}$ where $\|\mathbf{e}\|_2 = 1.0$:

$$\text{Cosine Similarity} = \frac{\mathbf{e}_{\text{ref}} \cdot \mathbf{e}_{\text{claimant}}}{\|\mathbf{e}_{\text{ref}}\|_2 \|\mathbf{e}_{\text{claimant}}\|_2}$$

- **Range:** Strictly clipped to $[-1.0, 1.0]$.
- **Critical Scientific Notice:** Cosine similarity is a directional metric in high-dimensional hyperspace. **It is NOT a probability or percentage confidence of identity.** A score of $0.85$ does NOT mean "85% confidence that the claimant is the speaker"; it must be evaluated strictly against an empirically calibrated decision threshold $\theta$.

### Decision Threshold & Scientific Calibration
- **Configurable:** Threshold $\theta \in [-1.0, 1.0]$ with default development threshold $\theta = 0.65$ (`dev-uncalibrated-v1.0`).
- **Version Tracking:** Every verification decision records the `threshold_version` used.
- **Scientific Notice on Calibration:** The development threshold is provided for functional software execution and must **not** be claimed as scientifically validated for production without empirical evaluation (EER optimization) on labeled human-speaker datasets with frozen development/test splits.

### Privacy, Compliance & Biometric Safeguards
- **Active-Only Verification:** Profiles in status `REVOKED` are immediately blocked (`ProfileRevokedError`, HTTP 403).
- **Zero Client-Supplied Embeddings:** API clients cannot submit external reference vectors; reference vectors are retrieved solely from verified local storage.
- **Biometric Vector Shielding:** Public responses (`VerificationResponse`) strictly withhold reference and candidate embedding arrays.
- **Configurable Score Exposure:** The raw numerical similarity score can be masked (`expose_similarity_score=False`) to prevent biometric side-channel reconstruction.
- **Immutable Audit Logging:** Append-only JSON lines log records transaction metadata, timestamps, and decision outcomes, while proactively rejecting payloads containing audio bytes or embedding vectors.

---

## 4. Pretrained ECAPA-TDNN Integration (Phase 2)

### Pretrained Model Provenance
SentinelAI uses the official pretrained model:
- **Identifier:** `speechbrain/spkrec-ecapa-voxceleb`
- **Architecture:** Emphasized Channel Attention, Propagation and Aggregation Time Delay Neural Network (ECAPA-TDNN).
- **Trained By:** SpeechBrain research team on the VoxCeleb 1 and VoxCeleb 2 datasets (7,000+ speakers).
- **Project Role:** Reused **strictly for pretrained inference**. This project did not train or fine-tune this model.
- **Hardware Optimization:** Fully validated for CPU inference on standard hardware (Intel Core i3, 8 GB RAM) without requiring CUDA.

---

## 5. Execution Commands

### 1. Run Complete Test Suite (153 Passed)
```bash
# Run all 153 tests across all phases (Audio, Speaker, Enrollment, Verification)
pytest -v

# Run Phase 4 Speaker Verification tests only (53 passed)
pytest -v tests/verification/

# Run Phase 3 Voice Enrollment tests only (37 passed)
pytest -v tests/enrollment/

# Run Phase 2 Speaker / ECAPA tests only (32 passed)
pytest -v tests/speaker/

# Run Phase 1 Audio Preprocessing tests only (31 passed)
pytest -v tests/test_audio_preprocessor.py tests/test_audio_api.py
```

### 2. Run Speaker Verification Demonstration
Executes an end-to-end enrollment, genuine match trial, impostor trial, missing profile handling, and revoked profile lockout:
```bash
python scripts/run_verification_demo.py
```

### 3. Run Voice Enrollment Demonstration
Executes multi-utterance enrollment aggregation, storage, and profile revocation:
```bash
python scripts/run_enrollment_demo.py
```

### 4. Run Pretrained Speaker Embedding Demo
Executes pretrained ECAPA-TDNN inference on CPU, extracting 192-dim embeddings and calculating cosine similarity:
```bash
python scripts/run_speaker_embedding_demo.py
```

### 5. Start FastAPI Server
```bash
uvicorn sentinelai.main:app --reload
```
Interactive OpenAPI Swagger docs: `http://127.0.0.1:8000/docs`

---

## 6. REST API Endpoints

### Audio Preprocessing (`/audio`)
- `POST /audio/preprocess`: Upload a WAV file for validation, resampling, and acoustic metric extraction.

### Voice Enrollment (`/enrollment`)
- `POST /enrollment/register`: Register a new speaker profile using $\ge 3$ WAV recordings with explicit consent.
- `GET /enrollment/profile/{profile_id}`: Retrieve safe public profile metadata (embeddings withheld).
- `GET /enrollment/status/{user_id}`: Check active enrollment status for a given user ID.
- `POST /enrollment/reenroll`: Re-enroll a user, superseding and purging the previous reference profile.
- `DELETE /enrollment/profile/{profile_id}`: Revoke a profile, permanently purging biometric embedding vectors while maintaining audit history.

### Speaker Verification (`/verification`)
- `POST /verification/verify`: Verify claimant identity comparing an uploaded WAV against an enrolled active profile.
- `GET /verification/health`: Check verification engine status, model load state, active device, and threshold version.

---

## 7. Python API Usage

### End-to-End Speaker Verification
```python
from sentinelai.speaker import SpeakerConfig, ECAPAModelLoader, SpeakerEmbeddingExtractor
from sentinelai.enrollment.storage import LocalFileProfileStorage
from sentinelai.verification import (
    VerificationConfig,
    SpeakerVerificationService,
    VerificationStatus,
)

# 1. Initialize ECAPA-TDNN extractor and profile storage
speaker_config = SpeakerConfig(device="cpu", normalize_embeddings=True)
loader = ECAPAModelLoader(config=speaker_config)
extractor = SpeakerEmbeddingExtractor(config=speaker_config, loader=loader)
storage = LocalFileProfileStorage(storage_dir="data/profiles")

# 2. Configure verification engine
verification_config = VerificationConfig(
    threshold_value=0.65,
    threshold_version="dev-uncalibrated-v1.0",
    expose_similarity_score=True,
)
service = SpeakerVerificationService(
    config=verification_config,
    extractor=extractor,
    storage=storage,
)

# 3. Verify claimant audio (WAV file path, bytes, or BytesIO)
response = service.verify_speaker(
    audio_input="claimant_recording.wav",
    user_id="user_alice_42",
)

# 4. Inspect verification outcome
if response.status == VerificationStatus.MATCH:
    print(f"[+] Verified! Score: {response.similarity_score:.4f} >= {verification_config.threshold_value}")
else:
    print(f"[-] Rejected! Score: {response.similarity_score:.4f} < {verification_config.threshold_value}")

print(f"Processing Latency: {response.processing_time_ms} ms")
print(f"Verification ID   : {response.verification_id}")
```

---

## 8. Research Evaluation Readiness

The verification architecture is designed to support formal academic biometric evaluation protocols once human-speaker research datasets are acquired:

- **Trial Generation:** Genuine trials ($H_0$: claimant is enrolled speaker) and Impostor trials ($H_1$: claimant is different speaker).
- **Error Rates:**
  - **False Acceptance Rate (FAR):** Fraction of impostor trials incorrectly classified as MATCH.
  - **False Rejection Rate (FRR):** Fraction of genuine trials incorrectly classified as NO_MATCH.
  - **Equal Error Rate (EER):** Operating threshold where $\text{FAR} = \text{FRR}$.
- **Performance Curves:** Receiver Operating Characteristic (ROC), Detection Error Tradeoff (DET), and Area Under Curve (AUC).
- **Protocol Boundary:** Synthetic audio is used strictly for functional software validation and pipeline regression testing. Real biometric performance figures must only be computed on human-speaker evaluation benchmarks with strictly separated development and evaluation splits.
