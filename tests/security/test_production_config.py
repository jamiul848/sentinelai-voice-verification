"""Tests for Sentinel Voice Production Configuration Security Validator.

Validates that weak development secrets, debug flags, wildcard CORS policies,
and invalid biometric encryption keys prevent startup in production environments.
"""

import pytest

from sentinelai.config import Settings
from sentinelai.security.config_validator import (
    ConfigurationSecurityError,
    validate_runtime_configuration,
)


def test_production_validator_rejects_default_secret_key():
    """Application startup must abort in production if SECRET_KEY is a default development placeholder."""
    prod_settings = Settings(
        environment="production",
        secret_key="sentinel_voice_dev_secret_key_change_in_production_32b",
        biometric_encryption_key="0123456789abcdef0123456789abcdef",
        csrf_secret_key="csrf_production_secure_token_key_32_chars!",
        debug=False,
        cors_origins=["https://sentinelvoice.io"],
    )

    with pytest.raises(ConfigurationSecurityError, match="SECRET_KEY must be a unique"):
        validate_runtime_configuration(prod_settings)


def test_production_validator_rejects_debug_mode():
    """Application startup must abort in production if DEBUG=True."""
    prod_settings = Settings(
        environment="production",
        secret_key="cryptographically_secure_random_production_secret_32b!",
        biometric_encryption_key="0123456789abcdef0123456789abcdef",
        csrf_secret_key="csrf_production_secure_token_key_32_chars!",
        debug=True,  # Insecure for production
        cors_origins=["https://sentinelvoice.io"],
    )

    with pytest.raises(ConfigurationSecurityError, match="DEBUG mode must be False"):
        validate_runtime_configuration(prod_settings)


def test_production_validator_rejects_wildcard_cors():
    """Application startup must abort in production if CORS origins contains wildcard '*'."""
    prod_settings = Settings(
        environment="production",
        secret_key="cryptographically_secure_random_production_secret_32b!",
        biometric_encryption_key="0123456789abcdef0123456789abcdef",
        csrf_secret_key="csrf_production_secure_token_key_32_chars!",
        debug=False,
        cors_origins=["*"],  # Wildcard strictly prohibited in prod
    )

    with pytest.raises(ConfigurationSecurityError, match=r"Wildcard '\*' in CORS origins"):
        validate_runtime_configuration(prod_settings)


def test_production_validator_rejects_missing_biometric_key():
    """Application startup must abort in production if biometric encryption key is missing."""
    prod_settings = Settings(
        environment="production",
        secret_key="cryptographically_secure_random_production_secret_32b!",
        biometric_encryption_key="",
        csrf_secret_key="csrf_production_secure_token_key_32_chars!",
        debug=False,
        cors_origins=["https://sentinelvoice.io"],
    )

    with pytest.raises(ConfigurationSecurityError, match="SENTINEL_BIOMETRIC_ENCRYPTION_KEY is required"):
        validate_runtime_configuration(prod_settings)


def test_production_validator_accepts_secure_configuration():
    """Application startup proceeds cleanly when all production parameters are secure."""
    prod_settings = Settings(
        environment="production",
        secret_key="cryptographically_secure_random_production_secret_32b!",
        biometric_encryption_key="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        csrf_secret_key="csrf_production_secure_token_key_32_chars!",
        debug=False,
        cors_origins=["https://sentinelvoice.io", "https://api.sentinelvoice.io"],
    )

    # Must complete without exception
    validate_runtime_configuration(prod_settings)
