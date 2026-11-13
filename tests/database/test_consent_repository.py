"""Unit tests for Sentinel Voice ConsentRepository."""

import pytest

from sentinelai.database.repositories.consent_repository import ConsentRepository
from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_and_fetch_consent_history(db_session):
    """Test creating biometric consent records and preserving complete history."""
    user_repo = UserRepository(db_session)
    consent_repo = ConsentRepository(db_session)

    user = await user_repo.create_user(
        email="consent_subject@domain.com",
        hashed_password="pw",
        full_name="Consent Subject",
    )

    # Initial check: no consent
    assert await consent_repo.get_latest_consent(user.id) is None

    # Record v1.0 consent
    c1 = await consent_repo.create_consent_record(
        user_id=user.id,
        consent_version="v1.0",
        consent_type="VOICE_BIOMETRIC_ENROLLMENT",
        ip_address="192.168.1.10",
    )
    assert c1.id is not None
    assert c1.consent_granted is True

    # Record updated v2.0 consent (e.g. policy renewal)
    c2 = await consent_repo.create_consent_record(
        user_id=user.id,
        consent_version="v2.0",
        consent_type="VOICE_BIOMETRIC_ENROLLMENT",
        ip_address="192.168.1.15",
    )
    assert c2.id is not None

    # Fetch latest consent: should be v2.0
    latest = await consent_repo.get_latest_consent(user.id)
    assert latest is not None
    assert latest.consent_version == "v2.0"

    # Full history: must contain BOTH records (never overwritten)
    history = await consent_repo.get_user_consent_history(user.id)
    assert len(history) == 2
    versions = [rec.consent_version for rec in history]
    assert "v1.0" in versions
    assert "v2.0" in versions

