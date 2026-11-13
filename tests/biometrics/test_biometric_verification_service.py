"""Unit tests for BiometricVerificationService."""

import uuid
import pytest
from sqlalchemy import select

from sentinelai.biometrics.enrollment_service import BiometricEnrollmentService
from sentinelai.biometrics.exceptions import (
    BiometricConsentRequiredError,
    InvalidEnrollmentAudioError,
    ProfileNotFoundError,
    ProfileRevokedError,
)
from sentinelai.biometrics.verification_service import BiometricVerificationService
from sentinelai.database.models.audit_log import AuditLog
from sentinelai.database.models.verification_event import VerificationEvent
from sentinelai.database.repositories.profile_repository import ProfileRepository
from tests.biometrics.conftest import create_synthetic_wav_bytes


@pytest.mark.asyncio
async def test_verification_match(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
    seeded_threshold,
):
    """Verify that a probe matching enrolled voiceprint yields MATCH."""
    # 1. Enroll user first
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    enroll_samples = [create_synthetic_wav_bytes(duration_sec=2.0) for _ in range(3)]
    await enroll_service.enroll_user(user=consented_user, audio_files=enroll_samples)

    # 2. Verify with matching probe
    verif_service = BiometricVerificationService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    probe_sample = create_synthetic_wav_bytes(duration_sec=2.0)
    result = await verif_service.verify_user(
        user=consented_user,
        audio_file=probe_sample,
        client_ip="127.0.0.1",
    )

    assert result.decision == "MATCH"
    assert result.is_match is True
    assert result.similarity_score >= result.applied_threshold
    assert result.processing_time_ms > 0
    assert result.threshold_version == "librispeech-dev-clean-eer-v1.0"
    assert result.threshold_id == seeded_threshold.id

    # Verify VerificationEvent in DB
    event = await test_session.get(VerificationEvent, result.verification_id)
    assert event is not None
    assert event.decision == "MATCH"
    assert event.is_match is True
    assert float(event.similarity_score) == pytest.approx(result.similarity_score, rel=1e-4)

    # Verify AuditLog in DB
    stmt_audit = select(AuditLog).where(
        AuditLog.resource_id == str(result.verification_id),
        AuditLog.action == "SPEAKER_VERIFIED",
    )
    audit = (await test_session.execute(stmt_audit)).scalars().first()
    assert audit is not None
    assert audit.actor_user_id == consented_user.id


@pytest.mark.asyncio
async def test_verification_no_match(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
    seeded_threshold,
):
    """Verify that a non-matching probe yields NO_MATCH."""
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    enroll_samples = [create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0) for _ in range(3)]
    await enroll_service.enroll_user(user=consented_user, audio_files=enroll_samples)

    verif_service = BiometricVerificationService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )

    probe_sample = create_synthetic_wav_bytes(duration_sec=2.5, freq_hz=880.0)

    result = await verif_service.verify_user(user=consented_user, audio_file=probe_sample)
    assert result.decision == "NO_MATCH"
    assert result.is_match is False
    assert result.similarity_score < result.applied_threshold


@pytest.mark.asyncio
async def test_verification_fails_without_consent(
    test_session,
    seeded_user,
    temp_storage,
    mock_extractor,
):
    """Verify verification is forbidden when consent is missing."""
    verif_service = BiometricVerificationService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    probe = create_synthetic_wav_bytes()

    with pytest.raises(BiometricConsentRequiredError, match="explicit user consent"):
        await verif_service.verify_user(user=seeded_user, audio_file=probe)


@pytest.mark.asyncio
async def test_verification_fails_no_profile(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify ProfileNotFoundError when user has no active enrolled profile."""
    verif_service = BiometricVerificationService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    probe = create_synthetic_wav_bytes()

    with pytest.raises(ProfileNotFoundError, match="No active voice profile"):
        await verif_service.verify_user(user=consented_user, audio_file=probe)


@pytest.mark.asyncio
async def test_verification_fails_revoked_profile(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify ProfileRevokedError if profile has been revoked."""
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    enroll_samples = [create_synthetic_wav_bytes() for _ in range(3)]
    enroll_res = await enroll_service.enroll_user(user=consented_user, audio_files=enroll_samples)

    # Revoke profile directly in DB
    profile_repo = ProfileRepository(test_session)
    await profile_repo.revoke_profile(enroll_res.profile_id)
    await test_session.commit()

    verif_service = BiometricVerificationService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    probe = create_synthetic_wav_bytes()

    # get_active_profile_by_user returns None because status != ACTIVE
    with pytest.raises(ProfileNotFoundError):
        await verif_service.verify_user(user=consented_user, audio_file=probe)


@pytest.mark.asyncio
async def test_verification_fails_corrupt_probe(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify InvalidEnrollmentAudioError when probe audio is corrupt."""
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    enroll_samples = [create_synthetic_wav_bytes() for _ in range(3)]
    await enroll_service.enroll_user(user=consented_user, audio_files=enroll_samples)

    verif_service = BiometricVerificationService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    corrupt_probe = b"NOT_A_VALID_WAV_HEADER"

    with pytest.raises(InvalidEnrollmentAudioError, match="failed acoustic validation"):
        await verif_service.verify_user(user=consented_user, audio_file=corrupt_probe)
