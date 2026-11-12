# SentinelAI – Autonomous Voice Verification Platform

SentinelAI Voice Verification research module for speaker identity verification, anti-spoofing, and voice defense pipelines.

---

## 1. Overview & Architecture

SentinelAI provides an independent, modular speaker recognition and voice verification software pipeline. It operates in structured research phases:

- **Phase 1 (Complete):** Audio Preprocessing, Header & Numeric Validation, Resampling to 16 kHz Mono, Acoustic Metrics.
- **Phase 2 (Complete):** Pretrained ECAPA-TDNN Integration, Fixed-Dimensional Speaker Embedding Extraction, L2 Normalization, and Directional Cosine Similarity.
- **Phase 3 (Complete):** Multi-Utterance Voice Enrollment, Reference Profile Aggregation, Secure Profile Storage, and Profile Revocation.
- **Phase 4 (Complete):** 1:1 Speaker Verification Engine, Configurable Decision Thresholding, Privacy-Preserving Audit Logging, and Verification API.
- **Phase 5A (Complete):** LibriSpeech Dataset Inspection, Acoustic Signal Validation, Demographic Annotation, Zero-Overlap Verification, and JSON/Markdown Reporting.
- **Phase 5B (Complete):** Multi-Speaker Enrollment & Trial Generation (Deterministic 3-recording enrollment, Genuine vs. Impostor Trials, Leakage Validation, Manifest Generation).
- **Phase 5C (Complete):** Threshold Calibration at Equal Error Rate (θ* = 0.6057, Dev EER = 3.41%), Frozen Test Evaluation (FAR = 1.94%, FRR = 2.65%), ROC/DET Visualizations, and Research Reporting.
- **Phase 6 (Upcoming):** Presentation Attack Detection (PAD) and Voice Anti-Spoofing Defense (Deepfake and physical replay detection).

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
├── verification/               # 1:1 Speaker Verification Engine (Phase 4)
│   ├── __init__.py             # Clean module exports
│   ├── config.py               # VerificationConfig (threshold, exposure toggle, audit paths)
│   ├── exceptions.py           # Verification domain exceptions (VerificationError, etc.)
│   ├── schemas.py              # VerificationResponse, VerificationHealthResponse, VerificationStatus
│   ├── scoring.py              # Cosine similarity scoring with clipping & dimension checks
│   ├── threshold.py            # VerificationThreshold manager with version tracking & bounds
│   ├── audit.py                # Append-only privacy-safe audit logging (JSON lines)
│   ├── service.py              # SpeakerVerificationService orchestrator
│   └── api.py                  # Verification APIRouter (/verification/*)
└── evaluation/                 # Dataset Inspection & Benchmark Evaluation (Phase 5)
    ├── __init__.py             # Clean module exports
    ├── dataset_inspector.py    # Recursive dataset scanner, SoundFile header inspector, overlap detector
    ├── dataset_report.py       # Data models, serialization, and Markdown report formatters
    ├── speaker_discovery.py    # Speaker & recording discovery, deterministic enrollment selection
    ├── batch_embedder.py       # Batch ECAPA-TDNN extraction with disk caching & resumability
    ├── trial_generator.py      # Genuine and impostor trial generation with reproducible seeding
    ├── trial_manifest.py       # CSV trial manifest & JSON summary writers/readers
    ├── leakage_validator.py    # Speaker-disjoint, recording non-overlap, label & duplicate validator
    ├── metrics.py              # FAR/FRR curves, continuous EER interpolation, ROC-AUC, classification metrics
    ├── threshold_calibrator.py # EER decision threshold calibration on dev data & immutable freezing
    ├── trial_scorer.py         # Cosine similarity scoring engine & sanitized score manifest generation
    ├── visualizer.py           # Matplotlib plotting (ROC, DET, FAR/FRR, distributions, confusion matrix)
    ├── evaluator.py            # End-to-end evaluation pipeline orchestrator across dev and test splits
    └── evaluation_report.py    # Markdown research report generator & JSON summary serializer
scripts/
├── run_preprocessing_demo.py   # Phase 1 standalone preprocessing runner
├── run_speaker_embedding_demo.py # Phase 2 standalone ECAPA-TDNN embedding runner
├── run_enrollment_demo.py      # Phase 3 standalone voice enrollment & revocation runner
├── run_verification_demo.py    # Phase 4 standalone speaker verification trial runner
├── inspect_librispeech.py      # Phase 5A CLI dataset inspection & validation tool
├── generate_verification_trials.py # Phase 5B CLI trial generation & manifest pipeline
└── run_evaluation.py           # Phase 5C CLI threshold calibration & benchmark evaluation
reports/
├── librispeech_inspection_report.json # Structured inspection metrics
├── librispeech_inspection_report.md   # Formatted markdown inspection report
└── evaluation/                 # Phase 5C Evaluation Artifacts
    ├── calibrated_threshold.json      # Calibrated operating threshold specification
    ├── development_metrics.json       # Development split performance metrics
    ├── test_metrics.json              # Unseen test split performance metrics (frozen threshold)
    ├── evaluation_report.md           # Formal scientific evaluation report
    └── figures/                       # Publication-quality benchmark figures (ROC, DET, FAR/FRR, CM)
outputs/
└── evaluation/
    ├── dev/                    # dev-clean trials (trials.csv, scores.csv, summary.json)
    └── test/                   # test-clean trials (trials.csv, scores.csv, summary.json)
notebooks/
└── ecapa_embedding_demo.ipynb  # Interactive Google Colab & local Jupyter demonstration
tests/
├── conftest.py                 # Audio test fixtures (synthetic mathematical tones)
├── test_audio_api.py           # FastAPI application and endpoint tests
├── test_audio_preprocessor.py  # Audio preprocessing unit tests
├── speaker/                    # Speaker module test suite (Phase 2)
├── enrollment/                 # Enrollment module test suite (Phase 3)
├── verification/               # Speaker verification test suite (Phase 4)
└── evaluation/                 # Evaluation test suite (Phase 5A, 5B & 5C)
    ├── __init__.py
    ├── test_dataset_inspector.py   # Unit tests for dataset inspector, audio health, overlap detection
    ├── test_trial_generator.py     # Unit tests for discovery, trial generation, leakage validation
    └── test_evaluation_metrics.py  # Unit tests for scoring, EER interpolation, ROC-AUC, freezing
```

---

## 2. Core Security Distinctions

To maintain scientific rigor and clear boundaries across security domains:

| Component | Responsibility | Question Answered | Phase |
| :--- | :--- | :--- | :--- |
| **Voice Enrollment** | Multi-utterance acoustic template creation & secure storage | *"How do we capture and model an authorized reference identity?"* | Phase 3 (Done) |
| **Speaker Verification** | 1:1 acoustic similarity evaluation against a decision threshold | *"Does this candidate recording match the claimed identity's profile?"* | Phase 4 (Done) |
| **Dataset Inspection** | Data health, audio property validation, and speaker overlap detection | *"Is this evaluation dataset valid, uncorrupted, and leakage-free?"* | Phase 5A (Done) |
| **Voice Anti-Spoofing (PAD)** | Presentation attack detection (replay, synthesis, deepfakes) | *"Is this voice genuine, live human speech or an artificial artifact?"* | Phase 6 (Upcoming) |

> [!IMPORTANT]
> **Speaker Verification alone is NOT a complete authentication system.**
> A matching voice recording can still be a physical acoustic replay, a voice conversion sample, or a text-to-speech deepfake. Production deployment strictly requires integration with Presentation Attack Detection (PAD), session authorization tokens, and replay defense.

---

## 3. Phase 5A: LibriSpeech Dataset Inspection & Validation

### Dataset Summary (`dev-clean` & `test-clean`)
The dataset inspection module (`sentinelai.evaluation.DatasetInspector`) recursively scans the dataset without reading audio arrays into memory, validating header integrity, sample rates, channels, durations, and speaker identity partitions:

| Metric | Overall Total | `dev-clean` | `test-clean` |
| :--- | :---: | :---: | :---: |
| **Unique Speakers** | **76** | 40 | 36 |
| **Audio Chapters** | **174** | 97 | 77 |
| **Total Utterances** | **5,075** | 2,703 | 2,372 |
| **Total Duration** | **10h 11m 01.55s** | 5h 23m 16.12s | 4h 47m 45.43s |
| **Mean Utterance Duration** | 7.22 s | 7.18 s (±4.70) | 7.28 s (±5.08) |
| **Min / Max Duration** | 1.28 s / 34.95 s | 1.45 s / 32.65 s | 1.28 s / 34.95 s |
| **Sample Rate** | **100% 16,000 Hz** | 16,000 Hz | 16,000 Hz |
| **Channels** | **100% Mono** | Mono | Mono |
| **Bit Depth / Subtype** | **Signed 16-bit PCM** | PCM_16 | PCM_16 |
| **Corrupted / Empty Files** | **0 / 0 (100% Valid)** | 0 / 0 | 0 / 0 |
| **Dev/Test Speaker Overlap** | **0 (Zero Leakage)** | Disjoint | Disjoint |

### Running Dataset Inspection CLI
```bash
python scripts/inspect_librispeech.py
```
Outputs are automatically compiled and saved to:
- Structured JSON: `reports/librispeech_inspection_report.json`
- Formatted Markdown: `reports/librispeech_inspection_report.md`

### Critical Scientific Limitations of LibriSpeech for Speaker Verification
1. **Read Speech Domain:** Utterances are readings from LibriVox audiobooks (neutral prosody, scripted speech), lacking conversational turn-taking, spontaneous hesitation, and vocal emotional shifts.
2. **High Acoustic Cleanliness:** High Signal-to-Noise Ratio (SNR) recorded under quiet, near-studio conditions; does not test reverberation or cross-channel acoustic microphone variations.
3. **ASR Heritage:** Compiled primarily for Automatic Speech Recognition (ASR); genuine and impostor trial pairs must be constructed programmatically rather than collected as natural multi-session claimant attempts.
4. **Suitability Determination:** Fully suitable as a clean, copyright-free, multi-speaker testbed for algorithm validation, genuine/impostor trial generation, and Equal Error Rate (EER) threshold calibration in Phase 5B/5C.

---

## 4. Phase 5B: Multi-Speaker Enrollment and Verification Trial Generation

### Objective & Architecture
Phase 5B constructs a reproducible, leakage-free evaluation trial dataset from LibriSpeech `dev-clean` and `test-clean`:

```
LibriSpeech Split (dev-clean / test-clean)
       │
       ▼
Speaker & Recording Discovery (sentinelai.evaluation.SpeakerRecordingDiscovery)
       │
       ▼
Deterministic Partitioning (sentinelai.evaluation.EnrollmentSelector)
  ├── 3 Enrollment Utterances per speaker (Reference Profile Generation)
  └── N - 3 Verification Utterances per speaker (Probe Trials)
       │
       ├──► Genuine Trials (label=1, same speaker probe)
       └──► Impostor Trials (label=0, cross-speaker probe sampled from disjoint speakers)
       │
       ▼
Data Leakage & Integrity Validation (sentinelai.evaluation.LeakageValidator)
  ├── Speaker-disjoint split verification (0 overlap between dev and test)
  ├── Enrollment / verification recording non-overlap
  ├── Label and identity consistency checks
  └── Duplicate trial & pair elimination
       │
       ▼
Trial Manifest Generation (sentinelai.evaluation.TrialManifestWriter)
  ├── outputs/evaluation/{dev,test}/trials.csv
  └── outputs/evaluation/{dev,test}/summary.json
```

### Trial Manifest Statistics

| Metric | `dev-clean` | `test-clean` | Combined Total |
| :--- | :---: | :---: | :---: |
| **Discovered Speakers** | 40 | 36 | 76 |
| **Eligible Speakers (≥4 recordings)** | 40 | 36 | 76 (100%) |
| **Ineligible Speakers** | 0 | 0 | 0 |
| **Enrollment Recordings (3/speaker)** | 120 | 108 | 228 |
| **Verification Recordings** | 2,583 | 2,264 | 4,847 |
| **Genuine Trials (label=1)** | 2,583 | 2,264 | 4,847 |
| **Impostor Trials (label=0, max 10/spk)** | 400 | 360 | 760 |
| **Total Evaluation Trials** | **2,983** | **2,624** | **5,607** |
| **Leakage Validation Status** | **PASSED (0 violations)** | **PASSED (0 violations)** | **ZERO LEAKAGE** |

### Data Leakage Prevention Guarantees
1. **Speaker Disjointness:** Development (`dev-clean`) and evaluation (`test-clean`) splits share exactly 0 speakers.
2. **Recording Non-Overlap:** No audio recording selected for enrollment is ever evaluated as a verification probe for that speaker.
3. **Reproducibility:** Partitioning and impostor selection use deterministic pseudo-random seeds (`seed=42`).
4. **Integrity Validation:** Every generated manifest is automatically checked by `LeakageValidator` before saving.

### Running Phase 5B Trial Generation CLI
```bash
# Generate trial manifests for dev-clean and test-clean (dry run, structure only)
python scripts/generate_verification_trials.py --skip-embedding-extraction

# Full pipeline including ECAPA-TDNN embedding extraction and reference profile aggregation
python scripts/generate_verification_trials.py
```

---

## 5. Phase 5C: Threshold Calibration and Performance Analysis

### Objective & Methodology
Phase 5C implements empirical decision threshold calibration and performance evaluation:
1. **Development Calibration (`dev-clean`):** Operating threshold $\theta^* = 0.6057$ is calibrated at the Equal Error Rate operating point ($\text{FAR} \approx \text{FRR}$) using continuous linear interpolation.
2. **Threshold Freezing:** Calibrated parameters are saved to `reports/evaluation/calibrated_threshold.json` and locked into `VerificationThreshold`.
3. **Unseen Test Evaluation (`test-clean`):** The exact frozen threshold $\theta^*$ is evaluated on test data without post-hoc tuning, preventing data leakage.
4. **Diagnostic Metrics:** In addition to operational error rates, test ROC-AUC and diagnostic EER are reported.

### Benchmark Evaluation Results

| Metric | Development Split (`dev-clean`) | Test Split (`test-clean`) |
| :--- | :---: | :---: |
| **Operating Decision Threshold** | **θ\* = 0.6057 (Calibrated)** | **θ\* = 0.6057 (Frozen)** |
| **Total Evaluation Trials** | 2,983 | 2,624 |
| **Genuine Trials (`label=1`)** | 2,583 | 2,264 |
| **Impostor Trials (`label=0`)** | 400 | 360 |
| **Equal Error Rate (EER)** | **3.41%** (Operating Point) | **2.47%** (Diagnostic only) |
| **Operational False Acceptance Rate (FAR)** | **3.50%** | **1.94%** |
| **Operational False Rejection Rate (FRR)** | **3.41%** | **2.65%** |
| **Classification Accuracy** | **96.58%** | **97.45%** |
| **Precision** | 99.44% | 99.68% |
| **Recall (1 - FRR)** | 96.59% | 97.35% |
| **F1-Score** | 0.9800 | 0.9850 |
| **ROC-AUC** | **0.9954** | **0.9976** |

### Running Phase 5C Benchmark Evaluation CLI
```bash
# Run benchmark evaluation and generate all reports and figures
python scripts/run_evaluation.py

# Run rapid synthetic demonstration
python scripts/run_evaluation.py --synthetic-demo
```
Generated reports and figures:
- [`reports/evaluation/calibrated_threshold.json`](file:///e:/sentinelai-voice-verification/reports/evaluation/calibrated_threshold.json)
- [`reports/evaluation/development_metrics.json`](file:///e:/sentinelai-voice-verification/reports/evaluation/development_metrics.json)
- [`reports/evaluation/test_metrics.json`](file:///e:/sentinelai-voice-verification/reports/evaluation/test_metrics.json)
- [`reports/evaluation/evaluation_report.md`](file:///e:/sentinelai-voice-verification/reports/evaluation/evaluation_report.md)
- [`reports/evaluation/figures/`](file:///e:/sentinelai-voice-verification/reports/evaluation/figures)

---

## 6. Execution Commands

### 1. Run Complete Test Suite (219 Passed)
```bash
# Run all 219 tests across all phases (Audio, Speaker, Enrollment, Verification, Evaluation)
pytest -v

# Run Phase 5 Evaluation tests only (66 passed: 10 in 5A + 38 in 5B + 18 in 5C)
pytest -v tests/evaluation/

# Run Phase 4 Speaker Verification tests only (53 passed)
pytest -v tests/verification/

# Run Phase 3 Voice Enrollment tests only (37 passed)
pytest -v tests/enrollment/

# Run Phase 2 Speaker / ECAPA tests only (32 passed)
pytest -v tests/speaker/

# Run Phase 1 Audio Preprocessing tests only (31 passed)
pytest -v tests/test_audio_preprocessor.py tests/test_audio_api.py
```

### 2. Run Speaker Verification Evaluation & Calibration (Phase 5C)
```bash
python scripts/run_evaluation.py
```

### 3. Run Verification Trial Generator (Phase 5B)
```bash
python scripts/generate_verification_trials.py --skip-embedding-extraction
```

### 4. Run LibriSpeech Dataset Inspector (Phase 5A)
```bash
python scripts/inspect_librispeech.py
```

### 5. Run Speaker Verification Demonstration
```bash
python scripts/run_verification_demo.py
```

### 6. Run Voice Enrollment Demonstration
```bash
python scripts/run_enrollment_demo.py
```

### 7. Start FastAPI Server
```bash
uvicorn sentinelai.main:app --reload
```
Interactive OpenAPI Swagger docs: `http://127.0.0.1:8000/docs`
