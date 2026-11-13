"""Tests for Sentinel Voice Operational Health Check Probes.

Validates /health, /health/live, /health/ready, and administrator-only /health/detailed.
Verifies critical security invariants: zero credential leakage and non-loading model checks.
"""

import pytest
from httpx import AsyncClient

from sentinelai.config import get_settings
from sentinelai.speaker.model import get_model_loader


@pytest.mark.asyncio
async def test_basic_health_endpoint(async_client: AsyncClient):
    """GET /health returns 200 OK with simple status."""
    res = await async_client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_liveness_probe(async_client: AsyncClient):
    """GET /health/live returns 200 OK with service metadata."""
    res = await async_client.get("/health/live")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_probe_connected(async_client: AsyncClient):
    """GET /health/ready returns 200 OK with verified DB connectivity."""
    res = await async_client.get("/health/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "database" in data["components"]
    assert data["components"]["database"]["status"] == "connected"


@pytest.mark.asyncio
async def test_detailed_health_unauthorized_and_forbidden(async_client: AsyncClient, seeded_user):
    """GET /health/detailed requires ADMIN privileges."""
    # 1. Unauthenticated request -> 401
    unauth_res = await async_client.get("/health/detailed")
    assert unauth_res.status_code == 401

    # 2. Standard USER login -> 403
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    user_token = login_res.json()["data"]["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    forbidden_res = await async_client.get("/health/detailed", headers=user_headers)
    assert forbidden_res.status_code == 403


@pytest.mark.asyncio
async def test_detailed_health_admin_success_and_invariants(async_client: AsyncClient, seeded_admin):
    """GET /health/detailed for ADMIN returns component metrics and respects invariants."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinelvoice.io", "password": "AdminSecurePass123!"},
    )
    admin_token = login_res.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    loader = get_model_loader()
    model_was_loaded = loader.is_loaded

    res = await async_client.get("/health/detailed", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    # Verify structural content
    assert data["status"] == "ready"
    assert "uptime_seconds" in data
    assert "ecapa_engine" in data
    assert "biometric_storage" in data
    assert "encryption_service" in data

    # INVARIANT 1: Health check must NEVER trigger model loading
    assert loader.is_loaded == model_was_loaded

    # INVARIANT 2: No sensitive credentials or secrets leaked
    settings = get_settings()
    res_text = res.text
    if settings.biometric_encryption_key:
        assert settings.biometric_encryption_key not in res_text
    assert settings.secret_key not in res_text
    assert "password" not in data["components"]["database"]

