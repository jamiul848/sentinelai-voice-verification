"""Sentinel Voice - Request Correlation & Tracing Module.

Provides distributed request correlation IDs across async tasks and HTTP lifecycles:
1. Validates or generates unique correlation IDs (UUID4).
2. Maintains request isolation via Python contextvars.
3. Automatically sets 'X-Request-ID' on all incoming request states and outgoing response headers.
4. Integrates with structured logging for end-to-end traceability.
"""

from contextvars import ContextVar
import re
from typing import Callable, Optional
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Header constant
REQUEST_ID_HEADER = "X-Request-ID"

# Safe correlation ID pattern: 8 to 64 alphanumeric chars, underscores, hyphens
REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{8,64}$")

# Thread-safe and task-isolated context variable
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id_ctx", default=None)


def get_current_request_id() -> Optional[str]:
    """Retrieve the correlation ID of the currently executing request task."""
    return request_id_ctx.get()


def validate_or_generate_request_id(incoming_header: Optional[str]) -> str:
    """Validate incoming X-Request-ID header or generate a high-entropy UUID4.

    Args:
        incoming_header: Optional raw header string from upstream client or proxy.

    Returns:
        Sanitized request correlation ID string.
    """
    if incoming_header and REQUEST_ID_PATTERN.match(incoming_header.strip()):
        return incoming_header.strip()
    return str(uuid.uuid4())


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware attaching correlation IDs to request state and response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        raw_header = request.headers.get(REQUEST_ID_HEADER.lower()) or request.headers.get(REQUEST_ID_HEADER)
        req_id = validate_or_generate_request_id(raw_header)

        # Bind to contextvar for async execution tree
        token = request_id_ctx.set(req_id)
        request.state.request_id = req_id

        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = req_id
            return response
        finally:
            request_id_ctx.reset(token)

