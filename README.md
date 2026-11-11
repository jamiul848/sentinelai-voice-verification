# SentinelAI – Autonomous Voice Verification Platform

SentinelAI Voice Verification research module for speaker identity verification, anti-spoofing, and voice defense pipelines.

---

## 1. Overview & Architecture

SentinelAI provides an independent, modular speaker recognition and voice verification software pipeline. It operates in structured research phases:

- **Phase 1 (Complete):** Audio Preprocessing, Header & Numeric Validation, Resampling to 16 kHz Mono, Acoustic Metrics.
- **Phase 2 (Current):** Pretrained ECAPA-TDNN Integration, Fixed-Dimensional Speaker Embedding Extraction, L2 Normalization, and Directional Cosine Similarity.
- **Phase 3 (Upcoming):** Multi-Utterance Voiceprint Enrollment, Threshold Calibration, and Verification/Authentication Endpoints.

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
└── speaker/                    # Speaker Recognition Module (Phase 2)
    ├── __init__.py             # Clean module exports
    ├── config.py               # SpeakerConfig (Pydantic model: device, model_source, cache)
    ├── exceptions.py           # Speaker domain exceptions (ModelLoadError, InvalidEmbeddingError)
    ├── model.py                # ECAPAModelLoader (lazy, thread-safe model caching)
    ├── embedding.py            # SpeakerEmbeddingExtractor & SpeakerEmbeddingResult
    └── similarity.py           # Directional Cosine Similarity Engine
scripts/
├── run_preprocessing_demo.py   # Phase 1 standalone preprocessing runner
└── run_speaker_embedding_demo.py # Phase 2 standalone ECAPA-TDNN embedding runner
notebooks/
└── ecapa_embedding_demo.ipynb  # Interactive Google Colab & local Jupyter demonstration
tests/
├── conftest.py                 # Audio test fixtures (synthetic mathematical tones)
├── test_audio_api.py           # FastAPI application and endpoint tests
├── test_audio_preprocessor.py  # Audio preprocessing unit tests
└── speaker/                    # Speaker module test suite
    ├── __init__.py
    ├── conftest.py             # Speaker fixtures & mock model classes
    ├── test_speaker_config.py  # Configuration & device validation tests
    ├── test_similarity.py      # Cosine similarity mathematical & edge case tests
    ├── test_model_loader_mocked.py # Fast unit tests for model loader caching
    ├── test_embedding_mocked.py# Fast unit tests for embedding extractor
    └── test_ecapa_integration.py # Real live pretrained ECAPA-TDNN inference test
```

---

## 2. Speaker Recognition Background

### What ECAPA-TDNN Does
**ECAPA-TDNN** (*Emphasized Channel Attention, Propagation and Aggregation Time Delay Neural Network*) is a state-of-the-art deep neural architecture for speaker recognition. It processes variable-length acoustic signals through multi-layer 1D convolutions with squeeze-and-excitation channel attention, aggregating frame-level features into a single, compact, fixed-dimensional speaker voiceprint vector.

### Difference Between Speaker Recognition and Voice Activity Detection (VAD)
- **Voice Activity Detection (VAD):** Detects *when* speech is present vs. non-speech (background noise, silence). It answers: *"Is someone speaking right now?"*
- **Speaker Recognition:** Identifies or verifies *who* is speaking by modeling the unique vocal tract geometry, pitch, and timbre. It answers: *"Is this specific voice Alice or Bob?"*

### What Speaker Embeddings Represent
A speaker embedding is a continuous, dense numerical vector (192 dimensions in `spkrec-ecapa-voxceleb`). It maps the identity characteristics of a voice onto an acoustic manifold:
- Utterances spoken by the **same person** produce vectors pointing in nearly the **same direction** (high cosine similarity).
- Utterances spoken by **different persons** produce vectors pointing in **divergent directions** (lower cosine similarity).

### Pretrained Model Provenance
SentinelAI uses the official pretrained model:
- **Identifier:** `speechbrain/spkrec-ecapa-voxceleb`
- **Trained By:** SpeechBrain research team on the VoxCeleb 1 and VoxCeleb 2 datasets (7,000+ speakers).
- **Project Role:** Reused **strictly for pretrained inference**. This project did not train or fine-tune this model.

---

## 3. Installation & Setup

### Environment Requirements
- Python $\ge$ 3.10
- Windows 11, Linux, or macOS
- Compatible with low-spec hardware (Intel Core i3, 8 GB RAM, no dedicated GPU needed)

### Install Dependencies
```bash
pip install -e .
```

### Git Hygiene
Model weights, Hugging Face checkpoint caches, and audio recordings (`*.wav`, `*.mp3`, etc.) are explicitly excluded via `.gitignore` to prevent committing heavy binaries or personal biometric recordings.

---

## 4. Execution Commands

### 1. Run All Tests (63 Passed)
```bash
# Run fast unit tests (audio + mocked speaker tests)
pytest -v

# Run only mocked speaker unit tests
pytest -v tests/speaker/test_speaker_config.py tests/speaker/test_similarity.py tests/speaker/test_model_loader_mocked.py tests/speaker/test_embedding_mocked.py

# Run live pretrained ECAPA-TDNN integration test
pytest -v tests/speaker/test_ecapa_integration.py
```

### 2. Run Speaker Embedding Demo (Standalone)
Executes pretrained ECAPA-TDNN inference on CPU, extracting 192-dim embeddings and calculating cosine similarity:
```bash
# Using synthetic test tones (no files required)
python scripts/run_speaker_embedding_demo.py

# Comparing two real consented audio recordings
python scripts/run_speaker_embedding_demo.py --audio1 "path/to/voice_a.wav" --audio2 "path/to/voice_b.wav"
```

### 3. Start FastAPI Server
```bash
uvicorn sentinelai.main:app --reload
```
Interactive OpenAPI Swagger docs: `http://127.0.0.1:8000/docs`

### 4. Run Google Colab Demonstration
Open `notebooks/ecapa_embedding_demo.ipynb` directly in Google Colab or locally in Jupyter Lab for an interactive visual walkthrough.

---

## 5. Python API Usage

```python
from sentinelai.speaker import (
    SpeakerConfig,
    ECAPAModelLoader,
    SpeakerEmbeddingExtractor,
    compute_cosine_similarity,
)

# 1. Configure module (device='auto' selects CUDA if available, else CPU)
config = SpeakerConfig(
    model_source="speechbrain/spkrec-ecapa-voxceleb",
    device="auto",
    normalize_embeddings=True,
)

# 2. Initialize loader (thread-safe, lazy loading with in-memory caching)
loader = ECAPAModelLoader(config=config)
extractor = SpeakerEmbeddingExtractor(config=config, loader=loader)

# 3. Extract speaker embedding from WAV file, bytes, or preprocessed tensor
result_a = extractor.extract("recording_a.wav", source_id="speaker_alice_01")
result_b = extractor.extract("recording_b.wav", source_id="speaker_alice_02")

# 4. Inspect extracted voiceprint metadata
print(f"Embedding Dimension : {result_a.dimension}")  # 192
print(f"Device Used         : {result_a.device}")     # 'cpu'
print(f"L2 Normalized       : {result_a.normalized}") # True (||e||_2 == 1.0)
print(f"Timestamp           : {result_a.extraction_timestamp}")

# 5. Compute Directional Cosine Similarity
similarity = compute_cosine_similarity(result_a, result_b)
print(f"Cosine Similarity   : {similarity:.4f}")
```

---

## 6. Current Boundaries & Next Steps

### Directional Cosine Similarity vs. Authentication
- Cosine similarity measures geometric alignment in the 192-dimensional embedding space:
  - $+1.0$: Identical acoustic trajectory.
  - $\sim 0.0$: Orthogonal (independent / distinct acoustic profiles).
  - $-1.0$: Opposite acoustic trajectory.
- **Current Limitation:** Cosine similarity alone does **not** prove identity. It requires:
  1. An empirically calibrated decision threshold (e.g., Equal Error Rate threshold on a validation cohort).
  2. Multi-utterance enrollment averaging ($\mathbf{e}_{\text{enrolled}} = \frac{\sum \mathbf{e}_i}{\|\sum \mathbf{e}_i\|}$).
  3. Liveness and anti-spoofing detection.

### Phase 3 Roadmap
1. Voiceprint Registry & Persistence (enrolling speaker identities with multi-utterance averaging).
2. Threshold Calibration & Verification Engine (decision logic: `ACCEPT` / `REJECT`).
3. RESTful Voice Enrollment (`/voice/enroll`) and Voice Verification (`/voice/verify`) Endpoints.
