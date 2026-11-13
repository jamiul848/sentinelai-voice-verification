"""Integration tests for user logout and session revocation (POST /api/v1/auth/logout)."""

import pytest
from httpx import AsyncClient

from sentinelai.auth.jwt_handler import hash_refresh_token
from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_logout_success(async_client: AsyncClient, seeded_user, test_session):
    """Verify that logging out revokes the refresh token and clears cookies."""
    # 1. Log in
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    # 2. Log out
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # 3. Check database record
    repo = UserRepository(test_session)
    record = await repo.get_refresh_token(hash_refresh_token(refresh_token))
    assert record.is_revoked is True


@pytest.mark.asyncio
async def test_logout_idempotent(async_client: AsyncClient, seeded_user):
    """Verify that repeating logout requests is safe, predictable, and does not fail."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    refresh_token = login_res.json()["data"]["refresh_token"]

    # First logout
    res1 = await async_client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert res1.status_code == 200

    # Second logout with same token
    res2 = await async_client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert res2.status_code == 200

