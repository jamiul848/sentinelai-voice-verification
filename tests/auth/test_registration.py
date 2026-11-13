"""Integration tests for user account registration endpoint (POST /api/v1/auth/register)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient):
    """Verify that valid registration payload creates a user with default USER role."""
    payload = {
        "full_name": "Alice Voice Researcher",
        "email": "alice.researcher@domain.com",
        "password": "SuperSecurePassword123!",
        "password_confirm": "SuperSecurePassword123!",
        "accept_privacy_terms": True,
    }

    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True
    assert "User registered successfully" in body["message"]

    user_data = body["data"]
    assert user_data["email"] == "alice.researcher@domain.com"
    assert user_data["full_name"] == "Alice Voice Researcher"
    assert user_data["is_active"] is True
    assert "USER" in user_data["roles"]
    assert "ADMIN" not in user_data["roles"]

    # Security Invariant: never leak password hash
    assert "hashed_password" not in user_data
    assert "password" not in user_data
    assert "embedding" not in user_data


@pytest.mark.asyncio
async def test_register_duplicate_email_rejected(async_client: AsyncClient):
    """Verify that registering an already registered email returns HTTP 409 Conflict."""
    payload = {
        "full_name": "Bob Duplicate",
        "email": "bob.dup@domain.com",
        "password": "Password123!@#",
        "password_confirm": "Password123!@#",
        "accept_privacy_terms": True,
    }

    # First registration
    r1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    # Second registration with duplicate email
    r2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already registered" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password_rejected(async_client: AsyncClient):
    """Verify that weak passwords failing complexity rules are rejected with HTTP 400/422."""
    payload = {
        "full_name": "Charlie Weak",
        "email": "charlie@domain.com",
        "password": "weak",
        "password_confirm": "weak",
        "accept_privacy_terms": True,
    }

    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_register_password_mismatch_rejected(async_client: AsyncClient):
    """Verify that mismatched password confirmation is rejected."""
    payload = {
        "full_name": "David Mismatch",
        "email": "david@domain.com",
        "password": "Password123!@#",
        "password_confirm": "DifferentPassword123!@#",
        "accept_privacy_terms": True,
    }

    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_register_without_privacy_terms_rejected(async_client: AsyncClient):
    """Verify that rejecting privacy terms prevents registration."""
    payload = {
        "full_name": "Eve Privacy",
        "email": "eve@domain.com",
        "password": "Password123!@#",
        "password_confirm": "Password123!@#",
        "accept_privacy_terms": False,
    }

    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code in [400, 422]

