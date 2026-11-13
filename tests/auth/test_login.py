"""Integration tests for user authentication and login endpoint (POST /api/v1/auth/login)."""

import pytest
from httpx import AsyncClient

from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, seeded_user):
    """Verify that valid credentials return token pair, CSRF token, and set HttpOnly cookie."""
    payload = {
        "email": "testuser@sentinelvoice.io",
        "password": "ValidPassword123!",
    }

    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 15 * 60  # 15 minutes
    assert data["csrf_token"] is not None
    assert data["user"]["email"] == "testuser@sentinelvoice.io"

    # Verify cookies
    cookies = response.cookies
    assert "sentinel_refresh_token" in cookies
    assert "sentinel_csrf_token" in cookies

    # Invariant: no password or hash exposure
    assert "hashed_password" not in data["user"]
    assert "token_hash" not in data


@pytest.mark.asyncio
async def test_login_incorrect_password(async_client: AsyncClient, seeded_user):
    """Verify that wrong password returns HTTP 401 Unauthorized."""
    payload = {
        "email": "testuser@sentinelvoice.io",
        "password": "WrongPassword123!",
    }

    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    """Verify that non-existent email returns identical generic 401 Unauthorized (no enumeration)."""
    payload = {
        "email": "does_not_exist@sentinelvoice.io",
        "password": "AnyPassword123!",
    }

    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(async_client: AsyncClient, seeded_user, test_session):
    """Verify that deactivated accounts cannot log in (HTTP 403 Forbidden)."""
    repo = UserRepository(test_session)
    await repo.deactivate_user(seeded_user.id)
    await test_session.commit()

    payload = {
        "email": "testuser@sentinelvoice.io",
        "password": "ValidPassword123!",
    }

    response = await async_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()

