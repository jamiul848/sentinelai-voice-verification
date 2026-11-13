"""Tests for Sentinel Voice Request Tracing and Correlation IDs.

Validates X-Request-ID propagation, generation, sanitization of malicious headers,
and async context variable isolation.
"""

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from sentinelai.main import create_app
from sentinelai.monitoring.request_tracing import (
    REQUEST_ID_HEADER,
    get_current_request_id,
    request_id_ctx,
    validate_or_generate_request_id,
)


def test_validate_or_generate_request_id_valid_custom():
    """Valid alphanumeric correlation IDs are accepted."""
    custom_id = "req_12345_prod_audit"
    assert validate_or_generate_request_id(custom_id) == custom_id


def test_validate_or_generate_request_id_malformed():
    """Hostile or invalid characters trigger automatic UUID4 generation."""
    # XSS injection attempt
    malicious = "<script>alert('xss')</script>"
    safe_generated = validate_or_generate_request_id(malicious)
    assert safe_generated != malicious
    assert len(safe_generated) == 36  # Standard UUID4 length

    # Empty / whitespace
    empty_generated = validate_or_generate_request_id("   ")
    assert len(empty_generated) == 36

    # Excessively long header (>64 chars)
    too_long = "a" * 100
    assert validate_or_generate_request_id(too_long) != too_long


@pytest.mark.asyncio
async def test_middleware_propagates_incoming_request_id():
    """Verify incoming X-Request-ID is preserved in response headers."""
    app = create_app()
    transport = ASGITransport(app=app)
    custom_id = "external-client-trace-9999"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/", headers={REQUEST_ID_HEADER: custom_id})
        assert res.status_code == 200
        assert res.headers.get(REQUEST_ID_HEADER) == custom_id


@pytest.mark.asyncio
async def test_middleware_generates_request_id_when_omitted():
    """Verify missing X-Request-ID produces an automatic UUID4."""
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        generated = res.headers.get(REQUEST_ID_HEADER)
        assert generated is not None
        assert len(generated) == 36


@pytest.mark.asyncio
async def test_async_contextvar_isolation():
    """Verify concurrent async coroutines do not leak or overwrite each other's correlation ID."""
    async def worker(trace_id: str) -> str:
        token = request_id_ctx.set(trace_id)
        await asyncio.sleep(0.01)
        current = get_current_request_id()
        request_id_ctx.reset(token)
        return current

    results = await asyncio.gather(
        worker("req-alpha-1111"),
        worker("req-bravo-2222"),
        worker("req-charlie-3333"),
    )

    assert results == ["req-alpha-1111", "req-bravo-2222", "req-charlie-3333"]

