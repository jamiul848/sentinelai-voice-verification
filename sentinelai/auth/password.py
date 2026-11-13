"""Sentinel Voice - Argon2id Password Hashing & Validation Service.

Enforces zero-trust credential security:
1. Passwords are never stored in plaintext.
2. Hashed using Argon2id (RFC 9106 recommended memory-hard hashing).
3. Validates password complexity before hashing.
4. Timing-safe verification prevents side-channel timing attacks.
"""

import re
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from sentinelai.auth.exceptions import WeakPasswordError

# Initialize Argon2id password hasher with production-grade parameters
# Memory: 64MB (65536 KiB), Time: 3 iterations, Parallelism: 2 threads
_PASSWORD_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

# Password complexity regex patterns
_UPPER_REGEX = re.compile(r"[A-Z]")
_LOWER_REGEX = re.compile(r"[a-z]")
_DIGIT_REGEX = re.compile(r"\d")
_SPECIAL_REGEX = re.compile(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def validate_password_strength(password: str) -> None:
    """Validate that a candidate password meets complexity requirements.

    Requirements:
    - Between 8 and 128 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special character

    Args:
        password: Plaintext password candidate.

    Raises:
        WeakPasswordError: If the password fails any requirement.
    """
    if not isinstance(password, str):
        raise WeakPasswordError("Password must be a valid string.")

    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password cannot exceed {MAX_PASSWORD_LENGTH} characters."
        )

    if not _UPPER_REGEX.search(password):
        raise WeakPasswordError("Password must contain at least one uppercase letter (A-Z).")

    if not _LOWER_REGEX.search(password):
        raise WeakPasswordError("Password must contain at least one lowercase letter (a-z).")

    if not _DIGIT_REGEX.search(password):
        raise WeakPasswordError("Password must contain at least one digit (0-9).")

    if not _SPECIAL_REGEX.search(password):
        raise WeakPasswordError(
            "Password must contain at least one special character (!@#$%^&* etc.)."
        )


def hash_password(password: str) -> str:
    """Validate complexity and compute Argon2id password hash.

    Args:
        password: Plaintext candidate password.

    Returns:
        Argon2id encoded hash string.

    Raises:
        WeakPasswordError: If password does not meet security requirements.
    """
    validate_password_strength(password)
    return _PASSWORD_HASHER.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a candidate password against an existing Argon2id hash.

    Uses timing-attack resistant verification.

    Args:
        plain_password: Raw candidate password.
        hashed_password: Stored Argon2id hash string.

    Returns:
        True if password matches, False otherwise.
    """
    if not plain_password or not hashed_password:
        return False

    try:
        return _PASSWORD_HASHER.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False

