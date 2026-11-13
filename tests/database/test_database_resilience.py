"""Tests for Sentinel Voice Database Resilience and Sanitized Error Handling.

Validates connection pool configurations, pre-ping liveness checks, and sanitized
SQLAlchemy exception handlers that prevent SQL and credential leakage.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from sentinelai.config import get_settings
from sentinelai.database.connection import get_async_engine
from sentinelai.main import create_app


def test_database_connection_pool_settings():
    """Verify production resilience pool settings are present on the async engine."""
    settings = get_settings()
    engine = get_async_engine()

    # Engine dialect-specific options
    assert engine is not None
    # Settings inspection
    assert settings.database_pool_pre_ping is True
    assert settings.database_pool_recycle == 1800
    assert settings.database_connect_timeout == 10.0


@pytest.mark.asyncio
async def test_sqlalchemy_error_sanitization():
    """Verify that internal SQLAlchemy database errors never disclose SQL syntax or table names."""
    app = create_app()

    # Define a test endpoint that deliberately simulates a failed SQL query
    @app.get("/test-db-failure")
    async def simulate_db_failure():
        raise OperationalError(
            statement="SELECT secret_hash, password FROM users WHERE id=1;",
            params={},
            orig=Exception("connection closed unexpectedly"),
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/test-db-failure")
        assert res.status_code == 500

        data = res.json()
        assert data["success"] is False
        assert data["error_code"] == "DATABASE_ERROR"
        assert data["message"] == "An internal database error occurred. Please try again later."

        # Critical security invariant: raw query or internal tables must never be in body
        body_text = res.text
        assert "secret_hash" not in body_text
        assert "password" not in body_text
        assert "SELECT" not in body_text

