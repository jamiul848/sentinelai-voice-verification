"""Test fixtures for the SentinelAI speaker verification module.

SCIENTIFIC AND ETHICAL GUARDRAIL:
All test audio signals used in these test fixtures are purely mathematical synthetic
signals (deterministic sine waves, harmonic signals, and silence arrays). They are
generated strictly for verifying software execution, input validation, dimensional
congruence, and storage state machines. They carry NO biometric validity and are not human speech.
"""

from datetime import datetime, timezone
import io
from pathlib import Path
from typing import List
import numpy as np
import pytest
import soundfile as sf
import torch

from sentinelai.audio.preprocessor import AudioPreprocessor
from sentinelai.enrollment.schemas import ProfileStatus, SpeakerProfile
from sentinelai.enrollment.storage import LocalFileProfileStorage
from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor, SpeakerEmbeddingResult
from sentinelai.speaker.model import ECAPAModelLoader
from sentinelai.verification.audit import InMemoryAuditLogger, JsonLinesAuditLogger
from sentinelai.verification.config import VerificationConfig
from sentinelai.verification.service import SpeakerVerificationService
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
def verification_storage(tmp_path: Path) -> LocalFileProfileStorage:
    """Provide an isolated local profile storage populated with enrolled test profiles."""
    storage_dir = tmp_path / "verification_profiles"
    storage = LocalFileProfileStorage(storage_dir=storage_dir)

    # Enrolled speaker A (e.g., "alice")
    # Base vector: normalized vector pointing mostly along first dimensions
    vec_a = np.zeros(192, dtype=np.float32)
    vec_a[:10] = 1.0
    vec_a = vec_a / np.linalg.norm(vec_a)

    profile_a = SpeakerProfile(
        profile_id="profile_alice_001",
        user_id="user_alice",
        reference_embedding=vec_a,
        embedding_dimension=192,
        model_name="speechbrain/spkrec-ecapa-voxceleb",
        enrollment_sample_count=3,
        consent_status=True,
        profile_status=ProfileStatus.ACTIVE,
    )
    storage.save_profile(profile_a)

    # Enrolled speaker B (e.g., "bob", orthogonal to alice)
    vec_b = np.zeros(192, dtype=np.float32)
    vec_b[50:60] = 1.0
    vec_b = vec_b / np.linalg.norm(vec_b)

    profile_b = SpeakerProfile(
        profile_id="profile_bob_002",
        user_id="user_bob",
        reference_embedding=vec_b,
        embedding_dimension=192,
        model_name="speechbrain/spkrec-ecapa-voxceleb",
        enrollment_sample_count=3,
        consent_status=True,
        profile_status=ProfileStatus.ACTIVE,
    )
    storage.save_profile(profile_b)

    # Revoked speaker profile (e.g., "charlie")
    vec_c = np.zeros(192, dtype=np.float32)
    vec_c[100:110] = 1.0
    vec_c = vec_c / np.linalg.norm(vec_c)

    profile_c = SpeakerProfile(
        profile_id="profile_charlie_003",
        user_id="user_charlie",
        reference_embedding=vec_c,
        embedding_dimension=192,
        model_name="speechbrain/spkrec-ecapa-voxceleb",
        enrollment_sample_count=3,
        consent_status=True,
        profile_status=ProfileStatus.REVOKED,
        revoked_at=datetime.now(timezone.utc),
        revocation_reason="User consent withdrawn",
    )
    storage.save_profile(profile_c)

    return storage


@pytest.fixture
def in_memory_audit_logger() -> InMemoryAuditLogger:
    """Provide an in-memory audit logger."""
    return InMemoryAuditLogger()


@pytest.fixture
def verification_service(
    verification_storage: LocalFileProfileStorage,
    mock_speaker_extractor: SpeakerEmbeddingExtractor,
    in_memory_audit_logger: InMemoryAuditLogger,
) -> SpeakerVerificationService:
    """Provide a configured SpeakerVerificationService with mock components."""
    config = VerificationConfig(
        threshold_value=0.65,
        threshold_version="dev-test-v1.0",
        expose_similarity_score=True,
        storage_dir=verification_storage.storage_dir,
    )
    return SpeakerVerificationService(
        config=config,
        extractor=mock_speaker_extractor,
        storage=verification_storage,
        audit_logger=in_memory_audit_logger,
    )


@pytest.fixture
def valid_candidate_audio_sample() -> bytes:
    """Generate a valid candidate audio sample (440 Hz, 1.5s)."""
    return create_synthetic_wav_bytes(freq_hz=440.0, duration_sec=1.5)


@pytest.fixture
def silent_audio_sample() -> bytes:
    """Generate a silent audio sample."""
    buffer = io.BytesIO()
    silence = np.zeros(16000, dtype=np.float32)
    sf.write(buffer, silence, 16000, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


@pytest.fixture
def corrupt_audio_sample() -> bytes:
    """Provide corrupted audio bytes."""
    return b"RIFF\x00\x00\x00\x00CORRUPT_WAVE_HEADER"


@pytest.fixture
def client_with_mock_verification(verification_service: SpeakerVerificationService):
    """Provide a TestClient with the isolated, mocked verification service injected."""
    from fastapi.testclient import TestClient
    from sentinelai.main import app
    from sentinelai.verification.api import get_verification_service

    app.dependency_overrides[get_verification_service] = lambda: verification_service
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

