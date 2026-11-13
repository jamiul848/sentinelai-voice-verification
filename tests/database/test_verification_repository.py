"""Unit tests for Sentinel Voice VerificationRepository."""

import uuid

import pytest

from sentinelai.database.repositories.user_repository import UserRepository
from sentinelai.database.repositories.verification_repository import (
    VerificationRepository,
)


@pytest.mark.asyncio
async def test_create_and_fetch_verification_events(db_session):
    """Test creating verification transactions and retrieving user history."""
    user_repo = UserRepository(db_session)
    verif_repo = VerificationRepository(db_session)

    user = await user_repo.create_user(
        email="verified_subject@voice.org",
        hashed_password="pw",
        full_name="Verified Subject",
    )

    # 1. Log MATCH event
    ev1 = await verif_repo.create_verification_event(
        user_id=user.id,
        decision="MATCH",
        similarity_score=0.745,
        applied_threshold=0.405898,
        is_match=True,
        processing_time_ms=134.2,
        client_ip="10.0.0.1",
    )
    assert ev1.id is not None
    assert ev1.decision == "MATCH"
    assert ev1.is_match is True

    # 2. Log NO_MATCH event
    ev2 = await verif_repo.create_verification_event(
        user_id=user.id,
        decision="NO_MATCH",
        similarity_score=0.231,
        applied_threshold=0.405898,
        is_match=False,
        processing_time_ms=128.5,
        client_ip="10.0.0.1",
    )
    assert ev2.id is not None
    assert ev2.decision == "NO_MATCH"
    assert ev2.is_match is False

    # 3. Fetch single event by UUID
    fetched = await verif_repo.get_verification_by_id(ev1.id)
    assert fetched is not None
    assert fetched.id == ev1.id

    # 4. Fetch history for user
    history = await verif_repo.get_user_verification_history(user.id)
    assert len(history) == 2
    assert history[0].id == ev2.id  # Ordered by created_at descending
    assert history[1].id == ev1.id

