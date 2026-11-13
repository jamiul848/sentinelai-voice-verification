"""Integration tests for user self-service endpoints (/api/v1/users/me, change-password)."""

import pytest
from httpx import AsyncClient

from sentinelai.auth.jwt_handler import hash_refresh_token
from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_get_current_user_profile(async_client: AsyncClient, seeded_user):
    """Verify that an authenticated user can retrieve their own sanitized profile."""
    # Log in
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["email"] == "testuser@sentinelvoice.io"
    assert data["full_name"] == "Standard Test User"
    assert "USER" in data["roles"]


@pytest.mark.asyncio
async def test_update_profile(async_client: AsyncClient, seeded_user):
    """Verify that an authenticated user can update permitted fields such as full name."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    update_res = await async_client.patch(
        "/api/v1/users/me",
        json={"full_name": "Updated User Full Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["data"]["full_name"] == "Updated User Full Name"


@pytest.mark.asyncio
async def test_change_password_success(async_client: AsyncClient, seeded_user, test_session):
    """Verify password change verifies current password, sets new hash, and invalidates sessions."""
    # 1. Log in
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]
    refresh_token = login_res.json()["data"]["refresh_token"]

    # 2. Change password
    change_res = await async_client.post(
        "/api/v1/users/change-password",
        json={
            "current_password": "ValidPassword123!",
            "new_password": "NewBrandSecurePass999!",
            "new_password_confirm": "NewBrandSecurePass999!",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_res.status_code == 200
    assert change_res.json()["success"] is True

    # 3. Invariant: previous refresh token is now revoked
    repo = UserRepository(test_session)
    old_record = await repo.get_refresh_token(hash_refresh_token(refresh_token))
    assert old_record.is_revoked is True

    # 4. Old password fails
    fail_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    assert fail_res.status_code == 401

    # 5. New password succeeds
    ok_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "NewBrandSecurePass999!"},
    )
    assert ok_res.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(async_client: AsyncClient, seeded_user):
    """Verify that providing an incorrect current password rejects the update."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]

    change_res = await async_client.post(
        "/api/v1/users/change-password",
        json={
            "current_password": "WrongCurrentPassword123!",
            "new_password": "NewBrandSecurePass999!",
            "new_password_confirm": "NewBrandSecurePass999!",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_res.status_code == 400
    assert "current password is incorrect" in change_res.json()["detail"].lower()

