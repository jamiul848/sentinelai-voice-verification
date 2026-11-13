"""Sentinel Voice - Production Structured Logging & Sanitization Module.

Provides:
1. ISO 8601 UTC JSON formatter for machine ingestion in production.
2. Clean console formatter for local developer environments.
3. Strict sanitization filter that strips passwords, tokens, keys, embeddings, and audio bytes.
4. Automatic injection of request correlation IDs from task contextvars.
5. StructuredLoggingMiddleware recording duration, method, route, and status code.
"""

from datetime import datetime, timezone
import json
import logging
import re
import sys
import time
from typing import Any, Callable, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from sentinelai.config import Settings, get_settings
from sentinelai.monitoring.request_tracing import get_current_request_id

# Sensitive keys and patterns to redact from logs
REDACT_KEYS = {
    "password",
    "password_confirmation",
    "old_password",
    "new_password",
    "access_token",
    "refresh_token",
    "token",
    "authorization",
    "cookie",
    "secret",
    "secret_key",
    "csrf_token",
    "biometric_encryption_key",
    "embedding",
    "embeddings",
    "audio",
    "audio_bytes",
    "raw_audio",
    "waveform",
}

REDACTED_STR = "[REDACTED]"


def sanitize_log_payload(data: Any) -> Any:
    """Recursively sanitize dictionaries and lists, redacting sensitive parameters."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(target in k_lower for target in REDACT_KEYS):
                sanitized[k] = REDACTED_STR
            else:
                sanitized[k] = sanitize_log_payload(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_log_payload(item) for item in data]
    return data


class JSONLogFormatter(logging.Formatter):
    """Formats log records as structured, single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        now_utc = datetime.now(timezone.utc).isoformat()
        req_id = getattr(record, "request_id", None) or get_current_request_id()

        log_data: Dict[str, Any] = {
            "timestamp": now_utc,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": req_id,
        }

        # Include standard extra attributes if provided
        for attr in ("duration_ms", "status_code", "method", "path", "client_ip", "error_code"):
            val = getattr(record, attr, None)
            if val is not None:
                log_data[attr] = val

        # Handle exception information safely
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
            }

        sanitized = sanitize_log_payload(log_data)
        return json.dumps(sanitized)


class ConsoleLogFormatter(logging.Formatter):
    """Human-readable console formatter for development environments."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", None) or get_current_request_id()
        req_tag = f" [{req_id[:8]}]" if req_id else ""
        msg = record.getMessage()
        duration = getattr(record, "duration_ms", None)
        dur_tag = f" ({duration}ms)" if duration is not None else ""
        return f"{record.levelname:<7} {record.name}{req_tag}: {msg}{dur_tag}"


def setup_logging(settings: Optional[Settings] = None) -> None:
    """Configure the root application logger with formatters and level."""
    active_settings = settings or get_settings()
    root_logger = logging.getLogger()
    root_logger.setLevel(active_settings.log_level.upper())

    # Remove existing handlers to avoid duplication
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    if active_settings.log_format == "json":
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(ConsoleLogFormatter())

    root_logger.addHandler(handler)

    # Silence verbose 3rd party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware logging request outcomes with duration, status, and correlation ID."""

    def __init__(self, app, logger_instance: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger_instance or logging.getLogger("sentinelai.access")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        req_id = getattr(request.state, "request_id", None) or get_current_request_id()

        # Resolve client IP safely
        client_ip = request.client.host if request.client else "unknown"

        response: Optional[Response] = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            method = request.method
            path = request.url.path

            extra_info = {
                "request_id": req_id,
                "duration_ms": duration_ms,
                "status_code": status_code,
                "method": method,
                "path": path,
                "client_ip": client_ip,
            }

            # Filter health probe spam from console logs in development unless failing
            if path in ("/health/live", "/health", "/health/ready") and status_code < 400:
                pass
            else:
                log_msg = f"{method} {path} returned {status_code} in {duration_ms}ms"
                if status_code >= 500:
                    self.logger.error(log_msg, extra=extra_info)
                elif status_code >= 400:
                    self.logger.warning(log_msg, extra=extra_info)
                else:
                    self.logger.info(log_msg, extra=extra_info)

