"""Tests for Sentinel Voice Structured Logging and Sanitization Module.

Validates JSON formatting, redaction of sensitive credentials, correlation IDs,
and request middleware latency logging.
"""

import json
import logging
import pytest
from httpx import ASGITransport, AsyncClient

from sentinelai.main import create_app
from sentinelai.monitoring.logging import (
    ConsoleLogFormatter,
    JSONLogFormatter,
    REDACTED_STR,
    sanitize_log_payload,
)


def test_sanitize_log_payload_redacts_sensitive_keys():
    """Verify passwords, tokens, embeddings, and keys are deeply redacted."""
    raw_payload = {
        "user_id": 123,
        "email": "analyst@sentinelvoice.io",
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
        "details": {
            "biometric_encryption_key": "raw_hex_key_32_bytes",
            "safe_metadata": "model_v2",
            "nested_list": [
                {"token": "secret_session_token", "normal_field": 42},
                {"embedding": [0.123, 0.456, 0.789]},
            ],
        },
    }

    sanitized = sanitize_log_payload(raw_payload)

    # Sensitive values must be replaced
    assert sanitized["password"] == REDACTED_STR
    assert sanitized["access_token"] == REDACTED_STR
    assert sanitized["details"]["biometric_encryption_key"] == REDACTED_STR
    assert sanitized["details"]["nested_list"][0]["token"] == REDACTED_STR
    assert sanitized["details"]["nested_list"][1]["embedding"] == REDACTED_STR

    # Safe non-sensitive values must be preserved
    assert sanitized["user_id"] == 123
    assert sanitized["email"] == "analyst@sentinelvoice.io"
    assert sanitized["details"]["safe_metadata"] == "model_v2"
    assert sanitized["details"]["nested_list"][0]["normal_field"] == 42


def test_json_log_formatter_structure():
    """Verify JSONLogFormatter generates valid JSON with correlation ID and ISO 8601 timestamp."""
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="sentinelai.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Operational audit event",
        args=(),
        exc_info=None,
    )
    record.request_id = "test-corr-uuid-12345"
    record.duration_ms = 45.2
    record.status_code = 200

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "sentinelai.test"
    assert parsed["message"] == "Operational audit event"
    assert parsed["request_id"] == "test-corr-uuid-12345"
    assert parsed["duration_ms"] == 45.2
    assert parsed["status_code"] == 200
    assert "timestamp" in parsed


def test_console_log_formatter():
    """Verify ConsoleLogFormatter generates clean human-readable logs."""
    formatter = ConsoleLogFormatter()
    record = logging.LogRecord(
        name="sentinelai.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=15,
        msg="Threshold adjustment required",
        args=(),
        exc_info=None,
    )
    record.request_id = "abcd1234efgh5678"
    record.duration_ms = 12.3

    output = formatter.format(record)
    assert "WARNING" in output
    assert "sentinelai.test [abcd1234]" in output
    assert "Threshold adjustment required" in output
    assert "(12.3ms)" in output


@pytest.mark.asyncio
async def test_structured_logging_middleware_invocation(caplog):
    """Verify StructuredLoggingMiddleware intercepts requests and emits log messages with duration."""
    caplog.set_level(logging.INFO)
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200

    # Ensure access log recorded the request
    access_logs = [record for record in caplog.records if record.name == "sentinelai.access"]
    assert len(access_logs) >= 1
    record = access_logs[0]
    assert record.method == "GET"
    assert record.path == "/"
    assert record.status_code == 200
    assert hasattr(record, "duration_ms")

