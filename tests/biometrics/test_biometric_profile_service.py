"""Unit tests for BiometricProfileService."""

from pathlib import Path
import pytest

from sentinelai.biometrics.enrollment_service import BiometricEnrollmentService
from sentinelai.biometrics.exceptions import ProfileNotFoundError
from sentinelai.biometrics.profile_service import BiometricProfileService
from sentinelai.biometrics.verification_service import BiometricVerificationService
from sentinelai.database.models.voice_profile import VoiceProfile
from tests.biometrics.conftest import create_synthetic_wav_bytes


@pytest.mark.asyncio
async def test_get_active_profile_and_samples(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify retrieval of active profile and sample records."""
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    samples = [create_synthetic_wav_bytes() for _ in range(3)]
    enroll_res = await enroll_service.enroll_user(user=consented_user, audio_files=samples)

    profile_service = BiometricProfileService(
        session=test_session,
        storage=temp_storage,
        enrollment_service=enroll_service,
    )

    detail = await profile_service.get_active_profile(consented_user.id)
    assert detail.id == enroll_res.profile_id
    assert detail.status == "ACTIVE"
    assert detail.sample_count == 3
    assert len(detail.enrollment_records) == 3


@pytest.mark.asyncio
async def test_get_active_profile_not_found(test_session, consented_user, temp_storage):
    """Verify ProfileNotFoundError when user has no active profile."""
    profile_service = BiometricProfileService(session=test_session, storage=temp_storage)
    with pytest.raises(ProfileNotFoundError):
        await profile_service.get_active_profile(consented_user.id)


@pytest.mark.asyncio
async def test_profile_re_enrollment(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify that re-enrollment shreds previous container and activates new profile."""
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    samples_initial = [create_synthetic_wav_bytes() for _ in range(3)]
    initial_res = await enroll_service.enroll_user(user=consented_user, audio_files=samples_initial)

    initial_path = Path(
        temp_storage.get_profile_path(consented_user.id, initial_res.profile_id)
    )
    assert initial_path.exists()

    profile_service = BiometricProfileService(
        session=test_session,
        storage=temp_storage,
        enrollment_service=enroll_service,
    )

    samples_new = [create_synthetic_wav_bytes() for _ in range(3)]
    re_res = await profile_service.re_enroll(user=consented_user, audio_files=samples_new)

    assert re_res.profile_id != initial_res.profile_id
    assert re_res.previous_profile_id == initial_res.profile_id

    # Verify old file was shredded
    assert not initial_path.exists()

    # Verify new file exists
    new_path = Path(temp_storage.get_profile_path(consented_user.id, re_res.profile_id))
    assert new_path.exists()

    # Verify old profile status in DB is REVOKED
    old_profile = await test_session.get(VoiceProfile, initial_res.profile_id)
    assert old_profile.status == "REVOKED"
    assert old_profile.revoked_at is not None


@pytest.mark.asyncio
async def test_profile_revocation(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
):
    """Verify that revoking a profile shreds vector container and sets status to REVOKED."""
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    samples = [create_synthetic_wav_bytes() for _ in range(3)]
    enroll_res = await enroll_service.enroll_user(user=consented_user, audio_files=samples)

    vector_path = Path(
        temp_storage.get_profile_path(consented_user.id, enroll_res.profile_id)
    )
    assert vector_path.exists()

    profile_service = BiometricProfileService(
        session=test_session,
        storage=temp_storage,
        enrollment_service=enroll_service,
    )

    revoke_res = await profile_service.revoke_profile(consented_user)
    assert revoke_res.status == "REVOKED"
    assert revoke_res.profile_id == enroll_res.profile_id

    # Verify file is shredded
    assert not vector_path.exists()

    # Verify get_active_profile now raises ProfileNotFoundError
    with pytest.raises(ProfileNotFoundError):
        await profile_service.get_active_profile(consented_user.id)


@pytest.mark.asyncio
async def test_verification_history_and_filtering(
    test_session,
    consented_user,
    temp_storage,
    mock_extractor,
    seeded_threshold,
):
    """Verify verification history queries with decision filtering and pagination."""
    enroll_service = BiometricEnrollmentService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )
    samples = [create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0) for _ in range(3)]
    await enroll_service.enroll_user(user=consented_user, audio_files=samples)

    verif_service = BiometricVerificationService(
        session=test_session,
        storage=temp_storage,
        extractor=mock_extractor,
    )

    # 1. Matching probe -> MATCH
    await verif_service.verify_user(
        user=consented_user,
        audio_file=create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0),
    )

    # 2. Impostor probe -> NO_MATCH
    await verif_service.verify_user(
        user=consented_user,
        audio_file=create_synthetic_wav_bytes(duration_sec=2.5, freq_hz=880.0),
    )

    profile_service = BiometricProfileService(
        session=test_session,
        storage=temp_storage,
        enrollment_service=enroll_service,
    )

    # All events
    history_all = await profile_service.get_verification_history(user_id=consented_user.id)
    assert history_all.total == 2
    assert len(history_all.items) == 2

    # Filter MATCH
    history_match = await profile_service.get_verification_history(
        user_id=consented_user.id,
        decision="MATCH",
    )
    assert history_match.total == 1
    assert history_match.items[0].decision == "MATCH"

    # Filter NO_MATCH
    history_no_match = await profile_service.get_verification_history(
        user_id=consented_user.id,
        decision="NO_MATCH",
    )
    assert history_no_match.total == 1
    assert history_no_match.items[0].decision == "NO_MATCH"
