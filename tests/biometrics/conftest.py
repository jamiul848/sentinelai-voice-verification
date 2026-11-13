"""Shared test fixtures for Phase 7D Voice Biometric Integration tests.

Provides:
- In-memory async SQLite engine with all models.
- Seeded threshold configuration matching Phase 5E calibration.
- Seeded user accounts with authenticated JWT headers.
- Biometric legal consent records.
- Deterministic synthetic audio waveforms.
- Mock ECAPA-TDNN embedding extractor for fast offline test execution.
"""

import io
from pathlib import Path
from typing import AsyncGenerator, Generator
import numpy as np
import pytest
import pytest_asyncio
import soundfile as sf
import torch
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sentinelai.auth.jwt_handler import create_access_token
from sentinelai.auth.password import hash_password
from sentinelai.biometrics.storage import BiometricStorageManager
from sentinelai.config import get_settings
from sentinelai.database.connection import get_db_session
from sentinelai.database.models import Base
from sentinelai.database.models.consent_record import ConsentRecord
from sentinelai.database.models.threshold_configuration import ThresholdConfiguration
from sentinelai.database.models.user import User
from sentinelai.database.repositories.user_repository import UserRepository
from sentinelai.main import app
from sentinelai.speaker.config import SpeakerConfig
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.model import ECAPAModelLoader
from tests.speaker.conftest import MockECAPAModel


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create an isolated in-memory SQLite async database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional AsyncSession bound to the in-memory engine."""
    session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def seeded_threshold(test_session: AsyncSession) -> ThresholdConfiguration:
    """Seed the Phase 5E calibrated baseline threshold configuration."""
    threshold = ThresholdConfiguration(
        version_tag="librispeech-dev-clean-eer-v1.0",
        model_identifier="speechbrain/spkrec-ecapa-voxceleb",
        threshold_value=0.405898,
        calibration_dataset="LibriSpeech dev-clean",
        calibration_criterion="EER",
        calibration_metadata={"eer": 0.052, "trials": 1200},
        is_active=True,
    )
    test_session.add(threshold)
    await test_session.commit()
    await test_session.refresh(threshold)
    return threshold


@pytest_asyncio.fixture(scope="function")
async def seeded_user(test_session: AsyncSession) -> User:
    """Create and seed a standard active user."""
    repo = UserRepository(test_session)
    user_role = await repo.get_role_by_name("USER")
    if not user_role:
        user_role = await repo.create_role(name="USER", description="Standard User")

    pw_hash = hash_password("ValidPassword123!")
    user = await repo.create_user(
        email="biometric_user@sentinelvoice.io",
        hashed_password=pw_hash,
        full_name="Biometric Test User",
        is_active=True,
        is_verified=True,
    )
    await repo.assign_role(user.id, user_role.id)
    await test_session.commit()
    return await repo.get_by_id(user.id)


@pytest_asyncio.fixture(scope="function")
async def consented_user(test_session: AsyncSession, seeded_user: User) -> User:
    """Provide a seeded user with active biometric legal consent."""
    consent = ConsentRecord(
        user_id=seeded_user.id,
        consent_type="VOICE_BIOMETRIC_ENROLLMENT",
        consent_granted=True,
        consent_version="1.0",
        ip_address="127.0.0.1",
    )
    test_session.add(consent)
    await test_session.commit()
    return seeded_user


@pytest_asyncio.fixture(scope="function")
def auth_headers(consented_user: User) -> dict:
    """Authorization header dictionary with valid bearer token for consented_user."""
    token = create_access_token(
        user_id=consented_user.id,
        email=consented_user.email,
        roles=["USER"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def second_user(test_session: AsyncSession) -> User:
    """Create a second distinct user for isolation and cross-account tests."""
    repo = UserRepository(test_session)
    user_role = await repo.get_role_by_name("USER")
    if not user_role:
        user_role = await repo.create_role(name="USER", description="Standard User")

    pw_hash = hash_password("ValidPassword123!")
    user = await repo.create_user(
        email="second_user@sentinelvoice.io",
        hashed_password=pw_hash,
        full_name="Second Test User",
        is_active=True,
        is_verified=True,
    )
    await repo.assign_role(user.id, user_role.id)
    consent = ConsentRecord(
        user_id=user.id,
        consent_type="VOICE_BIOMETRIC_ENROLLMENT",
        consent_granted=True,
        consent_version="1.0",
        ip_address="127.0.0.1",
    )
    test_session.add(consent)
    await test_session.commit()
    return await repo.get_by_id(user.id)


@pytest_asyncio.fixture(scope="function")
def second_auth_headers(second_user: User) -> dict:
    """Authorization header dictionary for second_user."""
    token = create_access_token(
        user_id=second_user.id,
        email=second_user.email,
        roles=["USER"],
    )
    return {"Authorization": f"Bearer {token}"}


class FastBiometricMockModel:
    """Mock model producing deterministic embeddings with distinct seeds for distinct audio."""

    def __init__(self, embedding_dim: int = 192) -> None:
        self.embedding_dim = embedding_dim
        self.eval_called = False

    def eval(self) -> "FastBiometricMockModel":
        self.eval_called = True
        return self

    def encode_batch(self, wavs: torch.Tensor, wav_lens: torch.Tensor = None) -> torch.Tensor:
        batch_size = wavs.shape[0] if wavs.ndim >= 2 else 1
        weights = torch.arange(1, wavs.shape[-1] + 1, device=wavs.device, dtype=torch.float32)
        val = float(torch.sum(wavs[0] * weights).item())
        data_hash = (int(abs(val) * 1000) % 99999) + 1
        generator = torch.Generator().manual_seed(data_hash)
        raw_emb = torch.randn((batch_size, 1, self.embedding_dim), generator=generator, dtype=torch.float32)
        return raw_emb


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch, tmp_path: Path):
    """Automatically mock ECAPA model loader and biometric store path for all tests in this package."""
    store_dir = tmp_path / "biometric_test_store"
    store_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    monkeypatch.setattr(settings, "biometric_store_path", store_dir)
    monkeypatch.setattr(
        settings,
        "biometric_encryption_key",
        "bXlfdGVzdF9tYXN0ZXJfa2V5XzMyYnl0ZXNfbG9uZw==",
    )

    mock_model = FastBiometricMockModel(embedding_dim=192)
    config = SpeakerConfig(device="cpu", normalize_embeddings=True)
    loader = ECAPAModelLoader(config=config)
    loader._model = mock_model
    loader._is_loaded = True

    monkeypatch.setattr("sentinelai.speaker.model.get_model_loader", lambda *a, **kw: loader)
    monkeypatch.setattr("sentinelai.speaker.embedding.get_model_loader", lambda *a, **kw: loader)

    yield


@pytest.fixture
def mock_extractor() -> SpeakerEmbeddingExtractor:
    """Provide a high-speed offline SpeakerEmbeddingExtractor backed by FastBiometricMockModel."""
    config = SpeakerConfig(device="cpu", normalize_embeddings=True)
    loader = ECAPAModelLoader(config=config)
    loader._model = FastBiometricMockModel(embedding_dim=192)
    loader._is_loaded = True
    return SpeakerEmbeddingExtractor(config=config, loader=loader)


@pytest.fixture
def temp_storage(tmp_path: Path) -> BiometricStorageManager:
    """Provide a BiometricStorageManager rooted in pytest tmp_path."""
    store_dir = tmp_path / "biometric_store"
    store_dir.mkdir(parents=True, exist_ok=True)
    return BiometricStorageManager(
        storage_root=store_dir,
        master_key="bXlfdGVzdF9tYXN0ZXJfa2V5XzMyYnl0ZXNfbG9uZw==",
    )


def create_synthetic_wav_bytes(
    duration_sec: float = 2.0,
    sample_rate: int = 16000,
    freq_hz: float = 440.0,
    dc_offset: float = 0.0,
) -> bytes:
    """Generate raw WAV bytes of a synthetic sine wave."""
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0.0, duration_sec, num_samples, endpoint=False)
    signal = (0.4 * np.sin(2.0 * np.pi * freq_hz * t) + dc_offset).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, signal, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


@pytest.fixture
def sample_wav_bytes() -> bytes:
    """Standard 2.0-second 16kHz mono WAV bytes (440 Hz)."""
    return create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0)


@pytest.fixture
def sample_wav_bytes_alt() -> bytes:
    """Alternative 2.0-second 16kHz mono WAV bytes (880 Hz)."""
    return create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=880.0)


@pytest_asyncio.fixture(scope="function")
async def async_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an AsyncClient with database session dependency overridden."""
    async def _override_get_db_session():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
