"""Unit tests for the ten Sentinel Voice SQLAlchemy 2.0 ORM Models."""

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from sentinelai.database.models import (
    ApiCredential,
    AuditLog,
    ConsentRecord,
    EnrollmentRecord,
    RefreshToken,
    Role,
    User,
    UserRole,
    VerificationEvent,
    VoiceProfile,
)


@pytest.mark.asyncio
async def test_user_email_normalization(db_session):
    """Test user model normalizes email addresses to lowercase and strips whitespace."""
    user = User(
        email="  Research.Lead@SentinelVoice.AI  ",
        hashed_password="secure_argon2id_hash_sample",
        full_name="Lead Researcher",
    )
    assert user.email == "research.lead@sentinelvoice.ai"

    db_session.add(user)
    await db_session.flush()

    assert isinstance(user.id, uuid.UUID)

    res = await db_session.execute(select(User).where(User.id == user.id))
    fetched = res.scalars().first()
    assert fetched.email == "research.lead@sentinelvoice.ai"


@pytest.mark.asyncio
async def test_user_unique_email_constraint(db_session):
    """Test unique email constraint prevents duplicate registrations."""
    u1 = User(
        email="analyst@domain.com",
        hashed_password="hash1",
        full_name="Analyst 1",
    )
    db_session.add(u1)
    await db_session.flush()

    u2 = User(
        email="ANALYST@domain.com",
        hashed_password="hash2",
        full_name="Analyst 2",
    )
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_role_and_user_role_assignment(db_session):
    """Test role creation, user assignment, and duplicate assignment rejection."""
    user = User(
        email="operator@test.com",
        hashed_password="hash",
        full_name="Operator",
    )
    role = Role(
        name="ADMIN",
        description="Administrator role",
        permissions=["users:read", "users:write"],
    )
    db_session.add_all([user, role])
    await db_session.flush()

    assert isinstance(role.id, uuid.UUID)

    assignment = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(assignment)
    await db_session.flush()

    # Attempt duplicate assignment
    dup_assignment = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(dup_assignment)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_refresh_token_and_api_credential_models(db_session):
    """Test refresh token session and developer API credential persistence."""
    user = User(
        email="dev_user@test.com",
        hashed_password="hash",
        full_name="Developer",
    )
    db_session.add(user)
    await db_session.flush()

    token = RefreshToken(
        user_id=user.id,
        token_hash="sha256_hash_of_refresh_token_value_here_64_chars_length_123456789",
        expires_at=datetime.now(timezone.utc),
        is_revoked=False,
    )
    cred = ApiCredential(
        user_id=user.id,
        name="Production IVR",
        key_prefix="sv_live_a1b2",
        key_hash="sha256_hash_of_api_key_secret_here_64_chars_length_1234567890abcdef",
        scopes=["verify"],
    )
    db_session.add_all([token, cred])
    await db_session.flush()

    assert token.id is not None
    assert cred.id is not None
    assert cred.is_active is True


@pytest.mark.asyncio
async def test_voice_profile_and_enrollment_records(db_session):
    """Test voice profile and acoustic enrollment records."""
    user = User(
        email="speaker_user@test.com",
        hashed_password="hash",
        full_name="Speaker Subject",
    )
    db_session.add(user)
    await db_session.flush()

    profile = VoiceProfile(
        user_id=user.id,
        status="ACTIVE",
        sample_count=3,
        mean_pairwise_similarity=0.895,
        model_identifier="speechbrain/spkrec-ecapa-voxceleb",
        embedding_storage_path="outputs/biometric_store/sample.enc",
        embedding_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )
    db_session.add(profile)
    await db_session.flush()

    record = EnrollmentRecord(
        profile_id=profile.id,
        duration_sec=3.45,
        rms_energy=0.042,
        peak_amplitude=0.31,
        snr_db=25.0,
        audio_format="FLAC",
    )
    db_session.add(record)
    await db_session.flush()

    assert record.id is not None
    assert record.audio_format == "FLAC"


@pytest.mark.asyncio
async def test_verification_event_and_audit_log(db_session):
    """Test verification event ledger and immutable audit log models."""
    user = User(
        email="audit_user@test.com",
        hashed_password="hash",
        full_name="Audit Subject",
    )
    db_session.add(user)
    await db_session.flush()

    verif = VerificationEvent(
        user_id=user.id,
        decision="MATCH",
        similarity_score=0.742,
        applied_threshold=0.405898,
        is_match=True,
        processing_time_ms=138.4,
        client_ip="127.0.0.1",
    )
    audit = AuditLog(
        actor_user_id=user.id,
        action="PROFILE_ENROLLMENT_COMPLETED",
        resource_type="voice_profile",
        resource_id=str(uuid.uuid4()),
        changes={"sample_count": 3},
    )
    db_session.add_all([verif, audit])
    await db_session.flush()

    assert verif.id is not None
    assert verif.decision == "MATCH"
    assert audit.id is not None
    assert audit.action == "PROFILE_ENROLLMENT_COMPLETED"
