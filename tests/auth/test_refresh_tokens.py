"""Integration tests for refresh token rotation, revocation, and breach detection."""

from datetime import timedelta
import pytest
from httpx import AsyncClient

from sentinelai.auth.jwt_handler import hash_refresh_token
from sentinelai.database.base import utc_now
from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_refresh_token_rotation_success(async_client: AsyncClient, seeded_user, test_session):
    """Verify that submitting a valid refresh token yields a new token pair and revokes the old one."""
    # 1. Log in to get initial refresh token
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    initial_data = login_res.json()["data"]
    initial_refresh = initial_data["refresh_token"]

    # 2. Rotate token
    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert refresh_res.status_code == 200

    new_data = refresh_res.json()["data"]
    new_refresh = new_data["refresh_token"]
    assert new_refresh != initial_refresh
    assert "access_token" in new_data

    # 3. Verify in database that the old token is marked revoked
    repo = UserRepository(test_session)
    old_hash = hash_refresh_token(initial_refresh)
    old_record = await repo.get_refresh_token(old_hash)
    assert old_record is not None
    assert old_record.is_revoked is True
    assert old_record.revoked_at is not None

    # Verify new token is active
    new_hash = hash_refresh_token(new_refresh)
    new_record = await repo.get_refresh_token(new_hash)
    assert new_record is not None
    assert new_record.is_revoked is False


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection(async_client: AsyncClient, seeded_user, test_session):
    """Verify that reusing a revoked refresh token triggers breach detection and family invalidation."""
    # 1. Log in
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    token_1 = login_res.json()["data"]["refresh_token"]

    # 2. Legitimate rotation to token_2
    r1 = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": token_1})
    assert r1.status_code == 200
    token_2 = r1.json()["data"]["refresh_token"]

    # 3. Attacker replays token_1 (which is already revoked)
    reuse_res = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": token_1})
    assert reuse_res.status_code == 401
    assert "reuse detected" in reuse_res.json()["detail"].lower()

    # 4. Invariant: token_2 must also be invalidated as part of family session revocation
    repo = UserRepository(test_session)
    token_2_record = await repo.get_refresh_token(hash_refresh_token(token_2))
    assert token_2_record.is_revoked is True

    # 5. Attempting to use token_2 now fails
    r3 = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": token_2})
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_expired(async_client: AsyncClient, seeded_user, test_session):
    """Verify that expired refresh tokens are rejected with HTTP 401."""
    repo = UserRepository(test_session)
    # Create an already expired token
    raw_token = "some_validly_formatted_expired_token_value_abc123"
    token_hash = hash_refresh_token(raw_token)
    await repo.create_refresh_token(
        user_id=seeded_user.id,
        token_hash=token_hash,
        expires_at=utc_now() - timedelta(hours=1),
    )
    await test_session.commit()

    res = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()

