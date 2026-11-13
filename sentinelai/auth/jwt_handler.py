"""Sentinel Voice - JWT Creation, Validation & Refresh Token Utilities.

Provides stateless access token generation (PyJWT) and high-entropy opaque refresh
token management with SHA-256 persistence hashing.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Tuple
import uuid

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError as PyJWTError

from sentinelai.auth.exceptions import InvalidTokenError, TokenExpiredError
from sentinelai.config import get_settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_ISSUER = "sentinelai-voice"


def create_access_token(
    user_id: uuid.UUID,
    email: str,
    roles: List[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed JWT access token.

    Args:
        user_id: Unique user UUID.
        email: User email address.
        roles: List of uppercase role names.
        expires_delta: Optional custom duration. Defaults to settings.access_token_expire_minutes.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expire = now + delta

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "roles": roles,
        "type": TOKEN_TYPE_ACCESS,
        "iss": TOKEN_ISSUER,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    token = jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: Raw JWT access token string.

    Returns:
        Decoded payload dictionary.

    Raises:
        TokenExpiredError: If the token expiration time has passed.
        InvalidTokenError: If signature, algorithm, issuer, or token type is invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=TOKEN_ISSUER,
            options={"require": ["sub", "exp", "iat", "type", "iss"]},
        )
    except ExpiredSignatureError as err:
        raise TokenExpiredError("Access token has expired.") from err
    except PyJWTError as err:
        raise InvalidTokenError(f"Invalid access token: {err}") from err

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise InvalidTokenError(f"Invalid token type: expected '{TOKEN_TYPE_ACCESS}'.")

    return payload


def generate_refresh_token() -> Tuple[str, str]:
    """Generate a cryptographically random refresh token and its SHA-256 hash.

    The raw token is transmitted to the client, while only the SHA-256 hex digest
    is persisted in the database.

    Returns:
        Tuple of (raw_token, token_hash).
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw_token)
    return raw_token, token_hash


def hash_refresh_token(raw_token: str) -> str:
    """Compute the SHA-256 hexadecimal digest of a raw refresh token.

    Args:
        raw_token: The plaintext refresh token string.

    Returns:
        64-character hexadecimal SHA-256 digest.
    """
    if not raw_token or not isinstance(raw_token, str):
        raise InvalidTokenError("Refresh token must be a non-empty string.")
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

