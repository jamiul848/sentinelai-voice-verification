"""Unit tests for Sentinel Voice ProfileRepository."""

import uuid

import pytest

from sentinelai.database.models import User
from sentinelai.database.repositories.profile_repository import ProfileRepository
from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_and_fetch_active_profile(db_session):
    """Test voice profile creation, sample linking, and active profile retrieval."""
    user_repo = UserRepository(db_session)
    profile_repo = ProfileRepository(db_session)

    user = await user_repo.create_user(
        email="enrolled_subject@voice.org",
        hashed_password="pw",
        full_name="Enrolled Subject",
    )

    profile = await profile_repo.create_profile(
        user_id=user.id,
        sample_count=3,
        mean_pairwise_similarity=0.887,
        embedding_storage_path="outputs/biometric_store/test_subject.enc",
        embedding_sha256="abc123sha256valuefortesting",
    )
    assert profile.id is not None
    assert profile.status == "ACTIVE"

    # Add 3 enrollment records
    for seq in (1, 2, 3):
        rec = await profile_repo.add_enrollment_record(
            profile_id=profile.id,
            duration_sec=3.5,
            rms_energy=0.035,
            peak_amplitude=0.28,
            audio_format="WAV",
            snr_db=23.0,
        )
        assert rec.id is not None

    # Fetch active profile
    active = await profile_repo.get_active_profile_by_user(user.id)
    assert active is not None
    assert active.id == profile.id
    assert len(active.enrollment_records) == 3


@pytest.mark.asyncio
async def test_superseding_profile_creation_revokes_prior(db_session):
    """Test creating a new profile automatically revokes the previous active profile."""
    user_repo = UserRepository(db_session)
    profile_repo = ProfileRepository(db_session)

    user = await user_repo.create_user(
        email="re_enrollment@voice.org",
        hashed_password="pw",
        full_name="Re-enroll Subject",
    )

    # First profile
    p1 = await profile_repo.create_profile(
        user_id=user.id,
        sample_count=3,
        mean_pairwise_similarity=0.85,
        embedding_storage_path="outputs/biometric_store/p1.enc",
        embedding_sha256="hash1",
    )
    assert p1.status == "ACTIVE"

    # Second profile (re-enrollment)
    p2 = await profile_repo.create_profile(
        user_id=user.id,
        sample_count=3,
        mean_pairwise_similarity=0.92,
        embedding_storage_path="outputs/biometric_store/p2.enc",
        embedding_sha256="hash2",
    )
    assert p2.status == "ACTIVE"

    # P1 should now be REVOKED
    p1_reloaded = await profile_repo.get_profile_by_id(p1.id)
    assert p1_reloaded.status == "REVOKED"
    assert p1_reloaded.revoked_at is not None

    # Active profile query returns P2
    current_active = await profile_repo.get_active_profile_by_user(user.id)
    assert current_active.id == p2.id


@pytest.mark.asyncio
async def test_revoke_profile_and_list_profiles(db_session):
    """Test revoking an active profile and listing with pagination."""
    user_repo = UserRepository(db_session)
    profile_repo = ProfileRepository(db_session)

    user = await user_repo.create_user(
        email="revocation_test@voice.org",
        hashed_password="pw",
        full_name="Revocation Subject",
    )

    profile = await profile_repo.create_profile(
        user_id=user.id,
        sample_count=3,
        mean_pairwise_similarity=0.89,
        embedding_storage_path="outputs/biometric_store/to_revoke.enc",
        embedding_sha256="hash_to_revoke",
    )

    # Revoke profile
    revoked = await profile_repo.revoke_profile(profile.id)
    assert revoked.status == "REVOKED"
    assert revoked.revoked_at is not None

    # Active query should now return None
    assert await profile_repo.get_active_profile_by_user(user.id) is None

    # List profiles for user
    profiles = await profile_repo.list_profiles(user_id=user.id)
    assert len(profiles) == 1
    assert profiles[0].status == "REVOKED"

