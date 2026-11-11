# SentinelAI – Autonomous Voice Verification Platform

SentinelAI Voice Verification research module for speaker identity verification, anti-spoofing, and voice defense pipelines.

---

## Audio Preprocessing Module

The audio preprocessing module prepares raw audio recordings for speaker embedding extraction with pretrained **ECAPA-TDNN** models (via SpeechBrain/PyTorch).

### Key Features
1. **WAV File Support**: Ingests audio from file paths (`str`, `pathlib.Path`), raw bytes (`bytes`), or binary streams (`io.BytesIO`).
2. **Stereo to Mono Downmixing**: Automatically downmixes multi-channel recordings to single-channel mono using channel averaging.
3. **Resampling**: High-quality polyphase/soxr resampling to the ECAPA-TDNN model sample rate (default `16000 Hz`).
4. **Recording Duration Validation**: Configurable `min_duration_sec` (default 0.5s) and `max_duration_sec` (default 30.0s) checks with explicit boundary enforcement.
5. **Empty & Corrupted File Detection**:
   - Rejects 0-byte files and truncated buffers.
   - Strictly validates `RIFF/WAVE` container headers.
   - Detects missing files and unreadable streams.
6. **Numerical Integrity & Safety**:
   - Detects `NaN` and `Infinity` numerical values.
   - Flags complete silence or signals below the RMS energy floor (`min_rms_energy`).
   - Detects digital clipping (`max_peak_amplitude > 1.0`).
7. **Quantitative Metrics**:
   - Computes duration, sample rate, sample count, RMS energy, and peak amplitude.
   - Provides decibel relative to full scale (dBFS) metrics (`rms_dbfs`, `peak_dbfs`).
8. **Configurable Settings**: Typed Pydantic configuration (`AudioPreprocessingConfig`) supporting custom sample rates, duration thresholds, silence flags, and peak normalization targets.
9. **Structured Output**: Returns `AudioPreprocessingResult` with:
   - `audio_tensor`: PyTorch `FloatTensor` formatted for ECAPA-TDNN (`[1, N]`).
   - `audio_numpy`: 1D `float32` NumPy array.
   - Detailed acoustic metrics and pipeline metadata.
   - Convenience export method `save_wav(...)` and serialization `to_dict()`.
10. **FastAPI Application**: Production-ready FastAPI app in `sentinelai.main` mounting the `/audio/preprocess` endpoint with interactive Swagger docs (`/docs`).

---

## Module Architecture

```
sentinelai/
├── __init__.py
├── main.py                 # FastAPI application entry point (app = create_app())
└── audio/
    ├── __init__.py         # Public API exports
    ├── api.py              # Audio APIRouter (/audio/preprocess)
    ├── cli.py              # Command-line interface
    ├── config.py           # AudioPreprocessingConfig (Pydantic model)
    ├── exceptions.py       # Custom exception hierarchy
    ├── metrics.py          # RMS energy, peak amplitude, dBFS calculations
    ├── preprocessor.py     # AudioPreprocessor and AudioPreprocessingResult
    └── validator.py        # Header, numeric, and duration validation logic
scripts/
└── run_preprocessing_demo.py # Standalone demonstration script
tests/
├── conftest.py             # Synthetic signal fixtures (pure mathematical tones)
├── test_audio_api.py       # FastAPI application and endpoint unit/integration tests
└── test_audio_preprocessor.py # Pipeline unit tests
```

---

## Execution Commands

### 1. Start the FastAPI Application Server
Run the Uvicorn ASGI server using the main application entry point:
```bash
uvicorn sentinelai.main:app --reload
```
Interactive API documentation will be available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

### 2. Run All Unit & Integration Tests
```bash
pytest -v
```

### 3. Run Demo with Synthetic Test Signal
Executes an end-to-end test on a dynamically generated 44.1 kHz stereo sine tone, downmixing to mono, resampling to 16 kHz, and exporting a preprocessed WAV:
```bash
python scripts/run_preprocessing_demo.py
```

### 4. Run Preprocessing via CLI
Preprocess an existing WAV audio file:
```bash
python -m sentinelai.audio.cli -i path/to/input.wav -o path/to/processed_16k_mono.wav
```

Run CLI synthetic demonstration without requiring existing audio:
```bash
python -m sentinelai.audio.cli --demo-synthetic
```

Output formatted JSON metrics:
```bash
python -m sentinelai.audio.cli --demo-synthetic --json
```

---

## Python API Usage

```python
from sentinelai.audio import AudioPreprocessor, AudioPreprocessingConfig

# 1. Configure settings (or use defaults)
config = AudioPreprocessingConfig(
    target_sample_rate=16000,
    min_duration_sec=0.5,
    max_duration_sec=30.0,
    normalize_audio=True,
    target_peak=0.95,
)

# 2. Initialize preprocessor
preprocessor = AudioPreprocessor(config=config)

# 3. Process audio (accepts file path, bytes, or BytesIO)
result = preprocessor.process("recording.wav")

# 4. Ingest into ECAPA-TDNN / SpeechBrain model
tensor = result.audio_tensor  # Shape: [1, num_samples], dtype: torch.float32

# 5. Access calculated metrics
print(f"Sample Rate: {result.sample_rate} Hz")
print(f"Duration   : {result.duration_sec:.2f} s")
print(f"RMS Energy : {result.rms_energy:.4f} ({result.metrics.rms_dbfs:.1f} dBFS)")
print(f"Peak       : {result.peak_amplitude:.4f}")

# 6. Save preprocessed audio to disk if needed
result.save_wav("cleaned_16k.wav")
```
