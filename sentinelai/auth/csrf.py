"""Sentinel Voice - Double-Submit CSRF Protection Utility.

Implements stateless Double-Submit Cookie CSRF protection:
1. When clients use cookie-based authentication, a random CSRF token is stored in
   a non-HttpOnly readable cookie (SameSite=Lax).
2. State-changing requests (POST, PATCH, DELETE, PUT) must provide the matching token
   in the 'X-CSRF-Token' HTTP header.
3. Requests authenticated via Bearer token in the 'Authorization' header are immune
   to cross-site request forgery and bypass CSRF checks.
"""

import secrets
from typing import Optional

from sentinelai.auth.exceptions import CSRFValidationError

CSRF_COOKIE_NAME = "sentinel_csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_csrf_token() -> str:
    """Generate a high-entropy URL-safe CSRF token.

    Returns:
        Random 32-byte URL-safe string.
    """
    return secrets.token_urlsafe(32)


def validate_double_submit_csrf(
    header_token: Optional[str],
    cookie_token: Optional[str],
) -> None:
    """Validate that the CSRF token in the request header matches the cookie token.

    Args:
        header_token: Value from 'X-CSRF-Token' header.
        cookie_token: Value from 'sentinel_csrf_token' cookie.

    Raises:
        CSRFValidationError: If either token is missing or they do not match.
    """
    if not header_token or not cookie_token:
        raise CSRFValidationError("CSRF token missing from request header or cookie.")

    if not secrets.compare_digest(header_token.strip(), cookie_token.strip()):
        raise CSRFValidationError("CSRF token validation failed: token mismatch.")

