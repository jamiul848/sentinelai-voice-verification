"""Unit tests for BiometricEnrollmentService."""

import uuid
import pytest
from sqlalchemy import select

from sentinelai.biometrics.enrollment_service import BiometricEnrollmentService
from sentinelai.biometrics.exceptions import (
    ActiveProfileAlreadyExistsError,
    BiometricConsentRequiredError,
    InsufficientEnrollmentSamplesError,
    InvalidEnrollmentAudioError,
)
from sentinelai.database.models.audit_log import AuditLog
from sentinelai.database.models.enrollment_record import EnrollmentRecord
from sentinelai.database.models.voice_profile import VoiceProfile
from tests.biometrics.conftest import create_synthetic_wav_bytes


@pytest.mark.asyncio
async def test_successful_enrollment(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify standard enrollment of 3 audio samples with DB and storage validation."""
    service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )

    audio_samples = [
        create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0),
        create_synthetic_wav_bytes(duration_sec=2.5, freq_hz=445.0),
        create_synthetic_wav_bytes(duration_sec=3.0, freq_hz=450.0),
    ]

    response = await service.enroll_user(
        user=consented_user,
        audio_files=audio_samples,
        client_ip="192.168.1.50",
    )

    assert response.profile_id is not None
    assert response.user_id == consented_user.id
    assert response.status == "ACTIVE"
    assert response.sample_count == 3
    assert len(response.samples) == 3
    assert response.mean_pairwise_similarity > 0.0

    # Verify Database VoiceProfile Record
    profile = await test_session.get(VoiceProfile, response.profile_id)
    assert profile is not None
    assert profile.status == "ACTIVE"
    assert profile.sample_count == 3
    assert profile.embedding_storage_path is not None
    assert profile.embedding_sha256 is not None

    # Verify EnrollmentRecords in Database
    stmt = select(EnrollmentRecord).where(EnrollmentRecord.profile_id == response.profile_id)
    result = await test_session.execute(stmt)
    records = list(result.scalars().all())
    assert len(records) == 3
    for r in records:
        assert float(r.duration_sec) >= 2.0
        assert r.audio_format == "WAV"
        assert float(r.rms_energy) > 0.0

    # Verify Audit Log Entry
    stmt_audit = select(AuditLog).where(
        AuditLog.resource_id == str(response.profile_id),
        AuditLog.action == "VOICE_PROFILE_ENROLLED",
    )
    audit = (await test_session.execute(stmt_audit)).scalars().first()
    assert audit is not None
    assert audit.actor_user_id == consented_user.id


@pytest.mark.asyncio
async def test_enrollment_fails_without_consent(
    test_session,
    seeded_user,
    temp_storage,
    mock_extractor,
):
    """Verify that enrollment is blocked if the user has not granted biometric consent."""
    service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )

    audio_samples = [create_synthetic_wav_bytes() for _ in range(3)]

    with pytest.raises(BiometricConsentRequiredError, match="explicit user consent"):
        await service.enroll_user(user=seeded_user, audio_files=audio_samples)


@pytest.mark.asyncio
async def test_enrollment_fails_with_active_profile(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify that enrolling twice without allow_replace raises ActiveProfileAlreadyExistsError."""
    service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )

    audio_samples = [create_synthetic_wav_bytes() for _ in range(3)]

    # First enrollment succeeds
    await service.enroll_user(user=consented_user, audio_files=audio_samples)

    # Second enrollment should fail
    with pytest.raises(ActiveProfileAlreadyExistsError, match="already registered"):
        await service.enroll_user(user=consented_user, audio_files=audio_samples, allow_replace=False)


@pytest.mark.asyncio
async def test_enrollment_fails_insufficient_samples(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify that providing fewer than 3 samples raises InsufficientEnrollmentSamplesError."""
    service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )

    audio_samples = [create_synthetic_wav_bytes() for _ in range(2)]

    with pytest.raises(InsufficientEnrollmentSamplesError, match="at least 3 valid"):
        await service.enroll_user(user=consented_user, audio_files=audio_samples)


@pytest.mark.asyncio
async def test_enrollment_fails_corrupt_audio(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify that corrupt audio payloads raise InvalidEnrollmentAudioError."""
    service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )

    audio_samples = [
        create_synthetic_wav_bytes(),
        b"CORRUPTED_HEADER_NOT_A_VALID_WAV_FILE",
        create_synthetic_wav_bytes(),
    ]

    with pytest.raises(InvalidEnrollmentAudioError, match="failed audio validation"):
        await service.enroll_user(user=consented_user, audio_files=audio_samples)
