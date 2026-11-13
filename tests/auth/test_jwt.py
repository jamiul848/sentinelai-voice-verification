"""Unit tests for JWT access token encoding/decoding and refresh token hashing."""

from datetime import timedelta
import uuid

import jwt
import pytest

from sentinelai.auth.exceptions import InvalidTokenError, TokenExpiredError
from sentinelai.auth.jwt_handler import (
    TOKEN_ISSUER,
    TOKEN_TYPE_ACCESS,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from sentinelai.config import get_settings


def test_create_and_decode_access_token():
    """Verify end-to-end access token creation and claim preservation."""
    user_id = uuid.uuid4()
    email = "researcher@sentinelvoice.io"
    roles = ["USER", "ANALYST"]

    token = create_access_token(user_id=user_id, email=email, roles=roles)
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["roles"] == roles
    assert payload["type"] == TOKEN_TYPE_ACCESS
    assert payload["iss"] == TOKEN_ISSUER
    assert "jti" in payload
    assert payload["exp"] > payload["iat"]


def test_expired_access_token_raises():
    """Verify that expired access tokens raise TokenExpiredError."""
    user_id = uuid.uuid4()
    token = create_access_token(
        user_id=user_id,
        email="expired@sentinelvoice.io",
        roles=["USER"],
        expires_delta=timedelta(seconds=-10),  # expired in the past
    )

    with pytest.raises(TokenExpiredError):
        decode_access_token(token)


def test_invalid_signature_raises():
    """Verify that tampering with the token signature raises InvalidTokenError."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, email="tamper@sentinelvoice.io", roles=["USER"])
    # Tamper with the token string
    tampered = token[:-5] + "XXXXX"

    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


def test_wrong_token_type_raises():
    """Verify that a token with non-'access' type is rejected."""
    settings = get_settings()
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "email": "test@test.com",
        "roles": ["USER"],
        "type": "refresh",  # wrong type
        "iss": TOKEN_ISSUER,
        "exp": 9999999999,
        "iat": 1000000000,
    }
    bogus_token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(InvalidTokenError, match="Invalid token type"):
        decode_access_token(bogus_token)


def test_generate_and_hash_refresh_token():
    """Verify refresh token generation produces high-entropy token and matching SHA-256 hash."""
    raw_token, token_hash = generate_refresh_token()

    assert len(raw_token) > 40
    assert len(token_hash) == 64  # SHA-256 produces 64 hex characters
    assert hash_refresh_token(raw_token) == token_hash

    # Different invocations produce distinct tokens
    raw2, hash2 = generate_refresh_token()
    assert raw_token != raw2
    assert token_hash != hash2

