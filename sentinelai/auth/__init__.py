"""Sentinel Voice - Authentication, Authorization & Cryptography Module."""

from sentinelai.auth.crypto import (
    decrypt_embedding_array,
    decrypt_vector_payload,
    encrypt_embedding_array,
    encrypt_vector_payload,
    generate_biometric_key,
    secure_delete_file,
)
from sentinelai.auth.exceptions import (
    AccountInactiveError,
    AuthError,
    CSRFValidationError,
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    LastAdminError,
    PasswordMismatchError,
    SelfModificationError,
    TokenExpiredError,
    TokenReusedError,
    UserNotFoundError,
    WeakPasswordError,
)
from sentinelai.auth.jwt_handler import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from sentinelai.auth.password import hash_password, validate_password_strength, verify_password
from sentinelai.auth.service import AuthService

__all__ = [
    "decrypt_vector_payload",
    "decrypt_embedding_array",
    "encrypt_vector_payload",
    "encrypt_embedding_array",
    "generate_biometric_key",
    "secure_delete_file",
    "hash_password",
    "validate_password_strength",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "generate_refresh_token",
    "hash_refresh_token",
    "AuthService",
    "AuthError",
    "InvalidCredentialsError",
    "AccountInactiveError",
    "EmailAlreadyExistsError",
    "WeakPasswordError",
    "PasswordMismatchError",
    "InvalidTokenError",
    "TokenExpiredError",
    "TokenReusedError",
    "InsufficientPermissionsError",
    "CSRFValidationError",
    "UserNotFoundError",
    "SelfModificationError",
    "LastAdminError",
]
