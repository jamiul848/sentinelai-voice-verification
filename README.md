# SentinelAI – Autonomous Voice Verification Platform

SentinelAI Voice Verification research module for speaker identity verification, anti-spoofing, and voice defense pipelines.

---

## 1. Overview & Architecture

SentinelAI provides an independent, modular speaker recognition and voice verification software pipeline. It operates in structured research phases:

- **Phase 1 (Complete):** Audio Preprocessing, Header & Numeric Validation, Resampling to 16 kHz Mono, Acoustic Metrics.
- **Phase 2 (Complete):** Pretrained ECAPA-TDNN Integration, Fixed-Dimensional Speaker Embedding Extraction, L2 Normalization, and Directional Cosine Similarity.
- **Phase 3 (Complete):** Multi-Utterance Voice Enrollment, Reference Profile Aggregation, Secure Profile Storage, and Profile Revocation.
- **Phase 4 (Upcoming):** Speaker Verification Engine, Threshold Calibration, and Decision Logic (`ACCEPT`/`REJECT`).
- **Phase 5 (Upcoming):** Liveness Detection and Voice Anti-Spoofing Defense (Deepfake/Replay detection).

```
sentinelai/
├── __init__.py
├── main.py                     # FastAPI application entry point (app = create_app())
├── audio/                      # Audio Preprocessing Module (Phase 1)
│   ├── __init__.py             # Public API exports
│   ├── api.py                  # Audio APIRouter (/audio/preprocess)
│   ├── cli.py                  # Command-line interface
│   ├── config.py               # AudioPreprocessingConfig (Pydantic model)
│   ├── exceptions.py           # Domain exception hierarchy
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
└── enrollment/                 # Voice Enrollment & Profile Management (Phase 3)
    ├── __init__.py             # Clean module exports
    ├── config.py               # EnrollmentConfig (min/max recordings, storage paths, consent)
    ├── exceptions.py           # Enrollment domain exceptions (ConsentError, StorageError, etc.)
    ├── schemas.py              # Pydantic schemas (SpeakerProfile, SpeakerProfilePublic, responses)
    ├── aggregation.py          # Reference embedding aggregation & consistency evaluation
    ├── storage.py              # Secure profile storage backend (JSON metadata + atomic .npz)
    ├── service.py              # EnrollmentService orchestrator
    └── api.py                  # Enrollment APIRouter (/enrollment/*)
scripts/
├── run_preprocessing_demo.py   # Phase 1 standalone preprocessing runner
├── run_speaker_embedding_demo.py # Phase 2 standalone ECAPA-TDNN embedding runner
└── run_enrollment_demo.py      # Phase 3 standalone voice enrollment & revocation runner
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
└── enrollment/                 # Enrollment module test suite (Phase 3)
    ├── __init__.py
    ├── conftest.py             # Enrollment fixtures, mock extractors, synthetic audio
    ├── test_enrollment_validation.py # Input validation, consent & recording limits
    ├── test_embedding_aggregation.py # Mathematical mean aggregation & consistency
    ├── test_profile_storage.py # Storage, persistence, and schema safety tests
    ├── test_profile_revocation.py # Revocation & biometric vector purging tests
    ├── test_enrollment_service.py # Core service lifecycle (enroll, reenroll, status)
    └── test_enrollment_api.py  # REST API integration & error handling tests
```

---

## 2. Voice Enrollment & Profile Management (Phase 3)

### System Objective
Phase 3 enables users to enroll their voice identity into a reference profile using multiple audio recordings. The system validates the inputs, extracts ECAPA-TDNN embeddings, computes an aggregated reference voiceprint vector, securely stores the profile, and supports re-enrollment and profile revocation with guaranteed biometric purging.

### Core Distinction: Enrollment vs. Verification vs. Anti-Spoofing
To maintain scientific clarity and security rigor:
- **Voice Enrollment (Phase 3):** Registration of a reference identity template from multiple consented recordings. Creates the baseline reference vector $\mathbf{e}_{\text{ref}}$.
- **Speaker Verification (Phase 4):** 1:1 comparison of an incoming claimant utterance $\mathbf{e}_{\text{claimant}}$ against the stored reference vector $\mathbf{e}_{\text{ref}}$, evaluated against an empirically calibrated decision threshold $\theta$.
- **Voice Anti-Spoofing / PAD (Phase 5):** Presentation Attack Detection evaluating whether a sample is genuine human speech vs. synthetic speech, voice conversion, or physical replay.

> [!IMPORTANT]
> Voice Enrollment alone is **not an authentication gate** and provides **no anti-spoofing defense**. It must not be deployed in production security contexts without Phase 4 verification calibration and Phase 5 liveness detection.

### Enrollment Architecture & Workflow
```
[User Audio Recordings] (≥ 3 WAV files) + Consent Confirmation
             │
             ▼
   [AudioPreprocessor] ──> Reject if corrupted, silent, or invalid duration
             │
             ▼
 [SpeakerEmbeddingExtractor] ──> Pretrained ECAPA-TDNN (192-dim vectors, L2 normalized)
             │
             ▼
   [Embedding Aggregator] ──> Mean vector calculation & intra-utterance consistency
             │
             ▼
  [ProfileStorageBackend] ──> .meta.json (Auditable metadata)
                              .emb.npz   (Biometric vector container)
             │
             ▼
[SpeakerProfilePublic] ──> Safe API response (Biometric vectors strictly withheld)
```

### Reference Embedding Aggregation
Given $N$ enrollment embeddings $\{\mathbf{e}_1, \mathbf{e}_2, \dots, \mathbf{e}_N\}$ where each $\|\mathbf{e}_i\|_2 = 1.0$:

1. **Mean Vector:**
   $$\mathbf{m} = \frac{1}{N} \sum_{i=1}^N \mathbf{e}_i$$

2. **L2 Unit Normalization:**
   $$\mathbf{e}_{\text{ref}} = \frac{\mathbf{m}}{\|\mathbf{m}\|_2}$$

3. **Intra-Utterance Consistency:**
   $$\text{Mean Pairwise Cosine Similarity} = \frac{2}{N(N - 1)} \sum_{i < j} (\mathbf{e}_i \cdot \mathbf{e}_j)$$

#### Documented Limitations of Arithmetic Mean Aggregation
- **Vulnerability to Outliers:** An uncharacteristic recording (e.g. background speech, cough, acoustic distortion) shifts the centroid away from the true speaker manifold.
- **Equal Weight Assumption:** All recordings contribute identically regardless of acoustic quality, SNR, or phoneme diversity.
- **Centroid Shrinkage:** High acoustic variance across utterances shortens $\|\mathbf{m}\|_2$ before normalization, potentially amplifying uninformative directions.

### Privacy, Compliance & Biometric Safeguards
SentinelAI implements privacy-by-design for biometric voice data:
- **Explicit Consent Required:** Enrollment requests without active consent (`consent=False`) are rejected immediately with `EnrollmentConsentError` (HTTP 400).
- **Zero Raw Audio Retention:** Voice audio bytes are processed strictly in-memory during inference and immediately discarded. No audio recordings are saved to disk.
- **Biometric Vector Shielding:** Public profile schemas (`SpeakerProfilePublic`) and all API endpoints strictly withhold embedding arrays to prevent unauthorized reconstruction or voice cloning attacks.
- **Right to Erasure (Revocation):** Revoking a profile (`DELETE /enrollment/profile/{profile_id}`) permanently unlinks and deletes the `.emb.npz` biometric container while retaining an auditable metadata record (`status="REVOKED"`).
- **Secure File Storage:** Stored using JSON and atomic NumPy `.npz` containers without Python `pickle` deserialization vulnerabilities.

---

## 3. Pretrained ECAPA-TDNN Integration (Phase 2)

### What ECAPA-TDNN Does
**ECAPA-TDNN** (*Emphasized Channel Attention, Propagation and Aggregation Time Delay Neural Network*) processes variable-length acoustic signals through multi-layer 1D convolutions with squeeze-and-excitation channel attention, aggregating frame-level features into a compact, fixed-dimensional (192-dim) speaker voiceprint vector.

### Pretrained Model Provenance
SentinelAI uses the official pretrained model:
- **Identifier:** `speechbrain/spkrec-ecapa-voxceleb`
- **Trained By:** SpeechBrain research team on the VoxCeleb 1 and VoxCeleb 2 datasets (7,000+ speakers).
- **Project Role:** Reused **strictly for pretrained inference**. This project did not train or fine-tune this model.
- **CPU Inference Support:** Fully optimized for standard multi-core CPUs without requiring dedicated CUDA hardware.

---

## 4. Installation & Setup

### Environment Requirements
- Python $\ge$ 3.10
- Windows 11, Linux, or macOS
- Compatible with low-spec hardware (Intel Core i3, 8 GB RAM, no dedicated GPU needed)

### Install Dependencies
```bash
pip install -e .
```

### Git Hygiene
Model weights, Hugging Face checkpoint caches, enrollment biometric containers (`data/profiles/*.npz`), and audio recordings are explicitly excluded via `.gitignore` to prevent committing heavy binaries or personal biometric recordings.

---

## 5. Execution Commands

### 1. Run Complete Test Suite (100 Passed)
```bash
# Run all tests (Audio, Speaker, Enrollment)
pytest -v

# Run Phase 3 Enrollment tests only
pytest -v tests/enrollment/

# Run Phase 2 Speaker & ECAPA tests only
pytest -v tests/speaker/

# Run Phase 1 Audio Preprocessing tests only
pytest -v tests/test_audio_preprocessor.py tests/test_audio_api.py
```

### 2. Run Voice Enrollment Demonstration
Executes an end-to-end enrollment cycle using 3 synthetic test tones, inspects reference aggregation, validates biometric storage, and executes profile revocation with biometric purging:
```bash
python scripts/run_enrollment_demo.py
```

### 3. Run Pretrained Speaker Embedding Demo
Executes pretrained ECAPA-TDNN inference on CPU, extracting 192-dim embeddings and calculating cosine similarity:
```bash
# Using synthetic test tones
python scripts/run_speaker_embedding_demo.py

# Comparing two real consented audio recordings
python scripts/run_speaker_embedding_demo.py --audio1 "path/to/voice_a.wav" --audio2 "path/to/voice_b.wav"
```

### 4. Start FastAPI Server
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

---

## 7. Python API Usage

### Multi-Utterance Voice Enrollment
```python
from sentinelai.enrollment import EnrollmentConfig, EnrollmentService
from sentinelai.speaker import SpeakerConfig, ECAPAModelLoader, SpeakerEmbeddingExtractor

# 1. Initialize extractor and storage
speaker_config = SpeakerConfig(device="cpu", normalize_embeddings=True)
loader = ECAPAModelLoader(config=speaker_config)
extractor = SpeakerEmbeddingExtractor(config=speaker_config, loader=loader)

enrollment_config = EnrollmentConfig(
    min_recordings=3,
    storage_dir="data/profiles",
    require_explicit_consent=True,
)
service = EnrollmentService(config=enrollment_config, extractor=extractor)

# 2. Register speaker profile (recordings can be file paths or bytes)
recordings = ["recordings/alice_01.wav", "recordings/alice_02.wav", "recordings/alice_03.wav"]
response = service.enroll(
    user_id="user_alice_42",
    recordings=recordings,
    consent_given=True,
    metadata={"environment": "quiet_room"},
)

print(f"Profile ID           : {response.profile_id}")
print(f"Number of Recordings : {response.recordings_used}")
print(f"Intra-Consistency    : {response.intra_speaker_consistency:.4f}")

# 3. Retrieve reference profile for verification (internal pipeline use)
profile = service.get_speaker_profile(response.profile_id)
print(f"Reference Embedding  : Shape {profile.reference_embedding.shape}")  # (192,)

# 4. Revoke profile (Purges biometric .npz file)
revocation = service.revoke_profile(response.profile_id, reason="User requested deletion")
print(f"Biometrics Purged    : {revocation.purged_biometrics}")  # True
```
