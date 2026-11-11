"""Test fixtures for the SentinelAI voice enrollment module.

SCIENTIFIC AND ETHICAL GUARDRAIL:
All test audio signals used in these test fixtures are purely mathematical synthetic
signals (deterministic sine tones, harmonic tones, and silence arrays). They are
generated strictly for verifying software execution, input validation, array shapes,
and storage transactions. They carry NO biometric validity and are not human speech.
"""

import io
from pathlib import Path
from typing import List
import numpy as np
import pytest
import soundfile as sf
import torch

from sentinelai.audio.preprocessor import AudioPreprocessor
from sentinelai.enrollment.config import EnrollmentConfig
from sentinelai.enrollment.service import EnrollmentService
from sentinelai.enrollment.storage import LocalFileProfileStorage
from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.model import ECAPAModelLoader
from tests.speaker.conftest import MockECAPAModel


def create_synthetic_wav_bytes(
    freq_hz: float = 440.0,
    sample_rate: int = 16000,
    duration_sec: float = 1.5,
    amplitude: float = 0.5,
) -> bytes:
    """Generate a valid, non-silent 16 kHz mono WAV file in bytes."""
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    signal = (amplitude * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, signal, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


@pytest.fixture
def mock_speaker_extractor() -> SpeakerEmbeddingExtractor:
    """Provide a fast, in-memory mock SpeakerEmbeddingExtractor producing 192-dim vectors."""
    mock_model = MockECAPAModel(embedding_dim=192)
    config = SpeakerConfig(device="cpu")
    loader = ECAPAModelLoader(config=config)
    loader._model = mock_model
    return SpeakerEmbeddingExtractor(config=config, loader=loader)


@pytest.fixture
def enrollment_storage(tmp_path: Path) -> LocalFileProfileStorage:
    """Provide a clean, isolated local profile storage in a temporary directory."""
    storage_dir = tmp_path / "enrollment_profiles"
    return LocalFileProfileStorage(storage_dir=storage_dir)


@pytest.fixture
def enrollment_service(
    enrollment_storage: LocalFileProfileStorage,
    mock_speaker_extractor: SpeakerEmbeddingExtractor,
) -> EnrollmentService:
    """Provide a configured EnrollmentService with mocked inference and isolated storage."""
    config = EnrollmentConfig(
        min_recordings=3,
        max_recordings=5,
        storage_dir=enrollment_storage.storage_dir,
        require_explicit_consent=True,
        purge_biometrics_on_revocation=True,
    )
    return EnrollmentService(
        config=config,
        storage=enrollment_storage,
        preprocessor=AudioPreprocessor(),
        extractor=mock_speaker_extractor,
    )


@pytest.fixture
def valid_enrollment_audio_samples() -> List[bytes]:
    """Provide 3 valid synthetic WAV recordings with distinct frequencies."""
    return [
        create_synthetic_wav_bytes(freq_hz=350.0, duration_sec=1.5),
        create_synthetic_wav_bytes(freq_hz=440.0, duration_sec=1.8),
        create_synthetic_wav_bytes(freq_hz=520.0, duration_sec=2.0),
    ]


@pytest.fixture
def corrupt_audio_sample() -> bytes:
    """Provide corrupted audio bytes."""
    return b"RIFF\x00\x00\x00\x00CORRUPT_NOT_WAVE_HEADER"


@pytest.fixture
def silent_audio_sample() -> bytes:
    """Provide a completely silent WAV audio recording (zeros)."""
    buffer = io.BytesIO()
    silence = np.zeros(16000, dtype=np.float32)
    sf.write(buffer, silence, 16000, format="WAV", subtype="PCM_16")
    return buffer.getvalue()

