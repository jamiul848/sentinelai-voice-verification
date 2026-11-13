"""Test fixtures and synthetic signal generators for audio preprocessing unit tests.

IMPORTANT NOTE:
All audio signals generated in this fixture suite are purely mathematical synthetic
signals (e.g., sine waves, deterministic tones, zero-arrays). None of these signals
represent or claim to represent human speech or real speaker data. They are designed
strictly for algorithmic unit testing of signal processing routines (resampling,
channel mixing, header parsing, duration validation, and numeric safety).
"""

import io
from pathlib import Path
from typing import Generator
import numpy as np
import pytest
import soundfile as sf


@pytest.fixture(autouse=True)
def reset_security_state():
    """Reset rate limiter and auth abuse trackers between tests.
    
    By default in unit/integration test suites, rate limiting is disabled so it does
    not cross-contaminate unrelated functional tests. Dedicated security tests
    explicitly enable rate limiting.
    """
    from sentinelai.config import get_settings
    from sentinelai.security.auth_abuse import get_auth_abuse_tracker
    from sentinelai.security.rate_limiter import get_rate_limiter_backend

    settings = get_settings()
    original_rate_limit_enabled = settings.rate_limit_enabled
    settings.rate_limit_enabled = False

    get_auth_abuse_tracker().clear()
    backend = get_rate_limiter_backend()
    if hasattr(backend, "clear"):
        backend.clear()

    yield

    settings.rate_limit_enabled = original_rate_limit_enabled
    get_auth_abuse_tracker().clear()
    if hasattr(backend, "clear"):
        backend.clear()


def create_synthetic_sine_tone(
    sample_rate: int = 16000,
    duration_sec: float = 2.0,
    freq_hz: float = 440.0,
    amplitude: float = 0.5,
    channels: int = 1,
) -> np.ndarray:
    """Generate a deterministic synthetic sine signal.

    NOTE: Purely synthetic mathematical test fixture. Not human speaker data.
    """
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0.0, duration_sec, num_samples, endpoint=False)
    if channels == 1:
        signal = (amplitude * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
        return signal
    else:
        # Multi-channel synthetic signal with slightly offset frequencies per channel
        channel_data = []
        for ch in range(channels):
            f = freq_hz * (1.0 + 0.5 * ch)
            channel_data.append(amplitude * np.sin(2.0 * np.pi * f * t))
        return np.column_stack(channel_data).astype(np.float32)


@pytest.fixture
def synthetic_mono_wav_16k(tmp_path: Path) -> Path:
    """Fixture providing a standard 16 kHz mono synthetic sine tone (2.0s)."""
    file_path = tmp_path / "synthetic_mono_16k.wav"
    data = create_synthetic_sine_tone(sample_rate=16000, duration_sec=2.0, freq_hz=440.0, channels=1)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_stereo_wav_44k(tmp_path: Path) -> Path:
    """Fixture providing a 44.1 kHz stereo synthetic tone (1.5s)."""
    file_path = tmp_path / "synthetic_stereo_44k.wav"
    data = create_synthetic_sine_tone(sample_rate=44100, duration_sec=1.5, freq_hz=440.0, channels=2)
    sf.write(str(file_path), data, 44100, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_low_sr_wav_8k(tmp_path: Path) -> Path:
    """Fixture providing an 8 kHz mono synthetic tone (1.0s)."""
    file_path = tmp_path / "synthetic_mono_8k.wav"
    data = create_synthetic_sine_tone(sample_rate=8000, duration_sec=1.0, freq_hz=300.0, channels=1)
    sf.write(str(file_path), data, 8000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_high_sr_wav_48k(tmp_path: Path) -> Path:
    """Fixture providing a 48 kHz mono synthetic tone (2.5s)."""
    file_path = tmp_path / "synthetic_mono_48k.wav"
    data = create_synthetic_sine_tone(sample_rate=48000, duration_sec=2.5, freq_hz=1000.0, channels=1)
    sf.write(str(file_path), data, 48000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_too_short_wav(tmp_path: Path) -> Path:
    """Fixture providing an excessively short synthetic signal (0.2s < min 0.5s)."""
    file_path = tmp_path / "synthetic_short.wav"
    data = create_synthetic_sine_tone(sample_rate=16000, duration_sec=0.2, freq_hz=440.0, channels=1)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_too_long_wav(tmp_path: Path) -> Path:
    """Fixture providing a synthetic signal exceeding max duration (35.0s > max 30.0s)."""
    file_path = tmp_path / "synthetic_long.wav"
    data = create_synthetic_sine_tone(sample_rate=16000, duration_sec=35.0, freq_hz=440.0, channels=1)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def synthetic_silent_wav(tmp_path: Path) -> Path:
    """Fixture providing a completely silent signal (all zeros, 1.0s)."""
    file_path = tmp_path / "synthetic_silent.wav"
    data = np.zeros(16000, dtype=np.float32)
    sf.write(str(file_path), data, 16000, subtype="PCM_16")
    return file_path


@pytest.fixture
def empty_wav_file(tmp_path: Path) -> Path:
    """Fixture providing a 0-byte file."""
    file_path = tmp_path / "empty_file.wav"
    file_path.write_bytes(b"")
    return file_path


@pytest.fixture
def corrupted_wav_file(tmp_path: Path) -> Path:
    """Fixture providing random corrupted bytes pretending to be a WAV file."""
    file_path = tmp_path / "corrupted.wav"
    file_path.write_bytes(b"RIFF\x00\x00\x00\x00NOT_A_WAVE_HEADER_CORRUPTED_BYTES_1234567890")
    return file_path


@pytest.fixture
def truncated_wav_file(tmp_path: Path) -> Path:
    """Fixture providing a truncated file of only 4 bytes."""
    file_path = tmp_path / "truncated.wav"
    file_path.write_bytes(b"RIFF")
    return file_path


# ------------------------------------------------------------------------------
# Authentication, Database & API Test Fixtures (Phase 7B & 7C)
# ------------------------------------------------------------------------------
from typing import AsyncGenerator
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sentinelai.auth.password import hash_password
from sentinelai.database.connection import get_db_session
from sentinelai.database.models import Base
from sentinelai.database.repositories.user_repository import UserRepository
from sentinelai.main import app


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create an isolated in-memory SQLite async database engine for fast API testing."""
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
async def async_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an AsyncClient with the database session dependency overridden."""
    async def _override_get_db_session():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seeded_user(test_session: AsyncSession):
    """Create and seed a standard active USER with known credentials."""
    repo = UserRepository(test_session)
    user_role = await repo.get_role_by_name("USER")
    if not user_role:
        user_role = await repo.create_role(name="USER", description="Standard User")

    pw_hash = hash_password("ValidPassword123!")
    user = await repo.create_user(
        email="testuser@sentinelvoice.io",
        hashed_password=pw_hash,
        full_name="Standard Test User",
        is_active=True,
        is_verified=True,
    )
    await repo.assign_role(user.id, user_role.id)
    await test_session.commit()
    return await repo.get_by_id(user.id)


@pytest_asyncio.fixture(scope="function")
async def seeded_admin(test_session: AsyncSession):
    """Create and seed an active ADMIN user."""
    repo = UserRepository(test_session)
    admin_role = await repo.get_role_by_name("ADMIN")
    if not admin_role:
        admin_role = await repo.create_role(name="ADMIN", description="Administrator")

    pw_hash = hash_password("AdminSecurePass123!")
    admin = await repo.create_user(
        email="admin@sentinelvoice.io",
        hashed_password=pw_hash,
        full_name="System Administrator",
        is_active=True,
        is_verified=True,
    )
    await repo.assign_role(admin.id, admin_role.id)
    await test_session.commit()
    return await repo.get_by_id(admin.id)

