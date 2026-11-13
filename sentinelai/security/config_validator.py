"""Sentinel Voice - Startup Security Configuration Validator.

Enforces production security posture before application begins serving traffic:
1. Rejects default development secret keys in production environments.
2. Rejects wildcard CORS policies in production.
3. Rejects missing or malformed biometric master encryption keys (AES-256).
4. Verifies debug mode is disabled in production.
5. Emits actionable warnings in development environments.
6. INVARIANT: Never prints, logs, or discloses cryptographic secret values.
"""

import logging
from typing import List, Optional

from sentinelai.auth.crypto import derive_key_bytes
from sentinelai.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Known development placeholder values that MUST NEVER be present in production
DEV_PLACEHOLDER_SECRETS = {
    "sentinel_voice_dev_secret_key_change_in_production_32b",
    "secret",
    "changeme",
    "password",
    "development",
}

DEV_PLACEHOLDER_CSRF = {
    "sentinel_voice_csrf_dev_secret_change_in_production",
    "csrf_secret",
    "changeme",
}


class ConfigurationSecurityError(RuntimeError):
    """Raised when runtime security configuration fails production safety invariants."""
    pass


def validate_runtime_configuration(settings: Optional[Settings] = None) -> None:
    """Validate application configuration against production security benchmarks.

    Args:
        settings: Optional Settings instance. Defaults to get_settings().

    Raises:
        ConfigurationSecurityError: If critical security configurations are invalid in production.
    """
    s = settings or get_settings()
    is_prod = s.environment == "production"
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Master Biometric Encryption Key Validation (AES-256 requires 32 bytes)
    if not s.biometric_encryption_key or not s.biometric_encryption_key.strip():
        if is_prod:
            errors.append("SENTINEL_BIOMETRIC_ENCRYPTION_KEY is required and cannot be empty in production.")
        else:
            warnings.append("SENTINEL_BIOMETRIC_ENCRYPTION_KEY is unset; biometric vector encryption will fail.")
    else:
        try:
            key_bytes = derive_key_bytes(s.biometric_encryption_key)
            if len(key_bytes) != 32:
                errors.append(f"Biometric encryption key resolved to {len(key_bytes)} bytes instead of 32 bytes.")
        except Exception as err:
            errors.append(f"Invalid biometric encryption key format: {type(err).__name__}.")

    # 2. JWT Signing Secret Key Validation
    if is_prod:
        if s.secret_key.strip() in DEV_PLACEHOLDER_SECRETS or len(s.secret_key.strip()) < 32:
            errors.append(
                "SECRET_KEY must be a unique, cryptographically secure string of at least 32 characters in production."
            )
    else:
        if s.secret_key.strip() in DEV_PLACEHOLDER_SECRETS:
            warnings.append("Using default development SECRET_KEY. Ensure this is replaced before production deployment.")

    # 3. CSRF Secret Key Validation
    if is_prod:
        if s.csrf_secret_key.strip() in DEV_PLACEHOLDER_CSRF or len(s.csrf_secret_key.strip()) < 32:
            errors.append(
                "CSRF_SECRET_KEY must be a unique, cryptographically secure string of at least 32 characters in production."
            )

    # 4. Debug Mode Guard
    if is_prod and s.debug:
        errors.append("DEBUG mode must be False in production deployment.")

    # 5. CORS Policy Guard
    if is_prod:
        if "*" in s.cors_origins:
            errors.append("Wildcard '*' in CORS origins is strictly prohibited in production mode.")

    # 6. Database Credentials Check
    if is_prod and ("localhost" in s.database_url or "sqlite" in s.database_url):
        warnings.append("Production database URL is referencing localhost or SQLite.")

    # Log any developmental warnings
    for warn in warnings:
        logger.warning("Security Configuration Advisory: %s", warn)

    # Halt initialization if production security invariants fail
    if errors:
        for err in errors:
            logger.critical("Production Security Invariant Violation: %s", err)
        error_summary = "; ".join(errors)
        raise ConfigurationSecurityError(
            f"Application startup aborted due to {len(errors)} production security configuration error(s): {error_summary}"
        )

    logger.info("Security configuration validated successfully for '%s' environment.", s.environment)
