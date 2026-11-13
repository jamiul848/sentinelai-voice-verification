"""Unit tests for Argon2id password hashing, strength validation, and verification."""

import pytest

from sentinelai.auth.exceptions import WeakPasswordError
from sentinelai.auth.password import hash_password, validate_password_strength, verify_password


def test_password_strength_valid():
    """Verify that a compliant password passes validation without exceptions."""
    valid_passwords = [
        "StrongPass123!",
        "V0ice#Sentinel_2026",
        "A1b2C3d4!@#$",
        "Complex_Phrase_With_99!",
    ]
    for pw in valid_passwords:
        validate_password_strength(pw)


def test_password_strength_too_short():
    """Verify that passwords shorter than 8 characters are rejected."""
    with pytest.raises(WeakPasswordError, match="at least 8 characters"):
        validate_password_strength("Aa1!")


def test_password_strength_missing_uppercase():
    """Verify rejection when uppercase letters are absent."""
    with pytest.raises(WeakPasswordError, match="uppercase"):
        validate_password_strength("alllowercase123!")


def test_password_strength_missing_lowercase():
    """Verify rejection when lowercase letters are absent."""
    with pytest.raises(WeakPasswordError, match="lowercase"):
        validate_password_strength("ALLLOWERCASE123!")


def test_password_strength_missing_digit():
    """Verify rejection when digits are absent."""
    with pytest.raises(WeakPasswordError, match="digit"):
        validate_password_strength("NoDigitsHere!@#")


def test_password_strength_missing_special_char():
    """Verify rejection when special characters are absent."""
    with pytest.raises(WeakPasswordError, match="special character"):
        validate_password_strength("NoSpecialChar12345")


def test_hash_password_argon2id_format():
    """Verify that hash_password produces a valid Argon2id hash string."""
    raw = "SecureVoicePass987!"
    hashed = hash_password(raw)

    assert hashed.startswith("$argon2id$")
    assert "m=65536" in hashed
    assert "t=3" in hashed
    assert "p=2" in hashed


def test_verify_password_success():
    """Verify that verify_password returns True for matching password."""
    raw = "CorrectPassword123!"
    hashed = hash_password(raw)

    assert verify_password(raw, hashed) is True


def test_verify_password_mismatch():
    """Verify that verify_password returns False for incorrect password."""
    raw = "CorrectPassword123!"
    hashed = hash_password(raw)

    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw, "") is False

