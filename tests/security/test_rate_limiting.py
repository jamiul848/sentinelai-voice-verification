"""Tests for Sentinel Voice API Rate Limiting Engine.

Validates sliding-window enforcement, HTTP 429 responses, Retry-After headers,
trusted proxy IP resolution, backend fallback, and configuration toggles.
"""

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from sentinelai.config import Settings, get_settings
from sentinelai.main import create_app
from sentinelai.security.rate_limiter import (
    InMemoryRateLimiterBackend,
    RateLimiter,
    RateLimitExceededError,
    get_trusted_client_ip,
    parse_rate_limit,
    set_rate_limiter_backend,
)


def test_parse_rate_limit_valid_expressions():
    """Verify various standard rate limit expressions parse correctly."""
    assert parse_rate_limit("5/minute") == (5, 60)
    assert parse_rate_limit("10/second") == (10, 1)
    assert parse_rate_limit("100/hour") == (100, 3600)
    assert parse_rate_limit("5/15minute") == (5, 900)
    assert parse_rate_limit("1000/day") == (1000, 86400)
    assert parse_rate_limit("20/30s") == (20, 30)


def test_parse_rate_limit_invalid_expressions():
    """Verify malformed rate limit expressions raise ValueError."""
    with pytest.raises(ValueError, match="Malformed rate limit"):
        parse_rate_limit("invalid")

    with pytest.raises(ValueError, match="Unknown time unit"):
        parse_rate_limit("10/lightyears")


def test_get_trusted_client_ip_direct_client():
    """Untrusted direct peer IP is returned; X-Forwarded-For is ignored."""
    scope = {
        "type": "http",
        "client": ("198.51.100.5", 54321),
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 10.0.0.1")],
    }
    req = Request(scope)
    # 198.51.100.5 is NOT in trusted proxies
    resolved = get_trusted_client_ip(req, trusted_proxies=["127.0.0.1", "10.0.0.1"])
    assert resolved == "198.51.100.5"


def test_get_trusted_client_ip_trusted_proxy_traversal():
    """When connecting through a trusted proxy, X-Forwarded-For is parsed right-to-left."""
    scope = {
        "type": "http",
        "client": ("10.0.0.1", 54321),  # Direct peer is trusted reverse proxy
        "headers": [(b"x-forwarded-for", b"203.0.113.50, 192.168.1.1, 10.0.0.2")],
    }
    req = Request(scope)
    trusted = ["10.0.0.1", "10.0.0.2", "192.168.1.1"]
    # 203.0.113.50 is the first non-trusted upstream IP
    resolved = get_trusted_client_ip(req, trusted_proxies=trusted)
    assert resolved == "203.0.113.50"


@pytest.mark.asyncio
async def test_in_memory_backend_sliding_window():
    """Verify in-memory backend sliding window correctly permits and throttles requests."""
    backend = InMemoryRateLimiterBackend()
    key = "test_user_1"

    # Allow 2 requests per 60 seconds
    allowed1, rem1, retry1 = await backend.check_rate_limit(key, max_requests=2, window_seconds=60)
    assert allowed1 is True
    assert rem1 == 1
    assert retry1 == 0

    allowed2, rem2, retry2 = await backend.check_rate_limit(key, max_requests=2, window_seconds=60)
    assert allowed2 is True
    assert rem2 == 0
    assert retry2 == 0

    # 3rd request must be blocked
    allowed3, rem3, retry3 = await backend.check_rate_limit(key, max_requests=2, window_seconds=60)
    assert allowed3 is False
    assert rem3 == 0
    assert retry3 > 0

    # Reset allows again
    await backend.reset(key)
    allowed4, rem4, retry4 = await backend.check_rate_limit(key, max_requests=2, window_seconds=60)
    assert allowed4 is True
    assert rem4 == 1


@pytest.mark.asyncio
async def test_rate_limit_disabled_by_config():
    """Verify that when rate_limit_enabled is False, requests are never throttled."""
    app = create_app()
    transport = ASGITransport(app=app)
    settings = get_settings()
    settings.rate_limit_enabled = False

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Multiple requests to root should all succeed
        for _ in range(15):
            res = await client.get("/")
            assert res.status_code == 200


@pytest.mark.asyncio
async def test_api_rate_limit_enforcement_and_headers():
    """Verify that exceeding route limit returns 429 and Retry-After header."""
    backend = InMemoryRateLimiterBackend()
    set_rate_limiter_backend(backend)

    settings = get_settings()
    settings.rate_limit_enabled = True

    app = create_app()
    limiter = RateLimiter("test_endpoint", default_limit="3/minute", key_type="ip")

    @app.get("/test-rate-limit", dependencies=[Depends(limiter)])
    async def rate_limited_endpoint():
        return {"status": "success"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First 3 requests succeed
        for i in range(3):
            res = await client.get("/test-rate-limit")
            assert res.status_code == 200
            assert "X-RateLimit-Limit" in res.headers
            assert res.headers["X-RateLimit-Limit"] == "3"
            assert "X-RateLimit-Remaining" in res.headers

        # 4th request must be rate limited with HTTP 429
        res4 = await client.get("/test-rate-limit")
        assert res4.status_code == 429
        data = res4.json()
        assert data["success"] is False
        assert data["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in res4.headers
        assert int(res4.headers["Retry-After"]) > 0


@pytest.mark.asyncio
async def test_rate_limiter_independent_client_ips():
    """Verify distinct client IPs maintain independent rate limit quotas."""
    backend = InMemoryRateLimiterBackend()
    set_rate_limiter_backend(backend)

    settings = get_settings()
    settings.rate_limit_enabled = True
    settings.trusted_proxies = ["127.0.0.1"]

    app = create_app()
    limiter = RateLimiter("test_ip_isolation", default_limit="2/minute", key_type="ip")

    @app.get("/test-ip-quota", dependencies=[Depends(limiter)])
    async def ip_isolated_endpoint():
        return {"status": "ok"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers_a = {"X-Forwarded-For": "198.51.100.10"}
        r1 = await client.get("/test-ip-quota", headers=headers_a)
        r2 = await client.get("/test-ip-quota", headers=headers_a)
        assert r1.status_code == 200
        assert r2.status_code == 200

        # IP A 3rd request fails
        r3 = await client.get("/test-ip-quota", headers=headers_a)
        assert r3.status_code == 429

        # IP B has independent quota and succeeds
        headers_b = {"X-Forwarded-For": "198.51.100.20"}
        r_b1 = await client.get("/test-ip-quota", headers=headers_b)
        assert r_b1.status_code == 200
