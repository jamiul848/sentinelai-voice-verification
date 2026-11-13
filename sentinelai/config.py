"""Sentinel Voice - Application Configuration & Settings.

Manages application configuration, database connection parameters, security secrets,
and biometric storage settings using Pydantic Settings and environment variables.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings and environment variable bindings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Application Metadata
    app_name: str = Field(default="Sentinel Voice", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application semver")
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    debug: bool = Field(default=False, description="Debug mode toggle")

    # PostgreSQL Database Settings
    database_url: str = Field(
        default="postgresql+asyncpg://sentinel:sentinel_secure_password@localhost:5432/sentinel_voice",
        description="Async database connection URL",
    )
    database_echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy query logging",
    )
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_max_overflow: int = Field(default=20, description="Max connection overflow")
    database_pool_recycle: int = Field(default=1800, description="Connection pool recycle duration in seconds")
    database_pool_pre_ping: bool = Field(default=True, description="Pre-ping connection before checkout")
    database_connect_timeout: float = Field(default=10.0, description="Database connection timeout in seconds")

    # API Rate Limiting Settings
    rate_limit_enabled: bool = Field(default=True, description="Master toggle for API rate limiting")
    redis_url: str | None = Field(
        default=None,
        alias="REDIS_URL",
        description="Redis connection URL for distributed rate limiting (e.g. redis://localhost:6379/0)",
    )
    rate_limit_storage: Literal["auto", "redis", "memory"] = Field(
        default="auto",
        description="Rate limiting backend storage type",
    )
    trusted_proxies: list[str] = Field(
        default=["127.0.0.1", "::1"],
        description="List of trusted upstream reverse proxy IP addresses for X-Forwarded-For parsing",
    )
    rate_limit_register: str = Field(
        default="5/hour",
        description="Registration rate limit per IP",
    )
    rate_limit_login: str = Field(
        default="5/15minute",
        description="Login rate limit per IP",
    )
    rate_limit_refresh: str = Field(
        default="10/15minute",
        description="Token refresh rate limit per user",
    )
    rate_limit_enrollment: str = Field(
        default="3/hour",
        description="Voice enrollment rate limit per user",
    )
    rate_limit_verification: str = Field(
        default="20/hour",
        description="Voice verification rate limit per user",
    )
    rate_limit_password_change: str = Field(
        default="5/hour",
        description="Password change rate limit per user",
    )
    rate_limit_general: str = Field(
        default="100/minute",
        description="General API rate limit per user/IP",
    )

    # Authentication Abuse Protection Settings
    auth_max_failed_logins: int = Field(
        default=5,
        description="Maximum consecutive failed login attempts before temporary account throttle",
    )
    auth_lockout_duration_seconds: int = Field(
        default=900,
        description="Temporary account throttling lockout duration in seconds (15 minutes)",
    )
    auth_ip_max_failed_attempts: int = Field(
        default=15,
        description="Maximum failed attempts from a single IP before temporary IP throttle",
    )
    auth_ip_lockout_duration_seconds: int = Field(
        default=900,
        description="Temporary IP throttling lockout duration in seconds (15 minutes)",
    )

    # Biometric Inference & Upload Resource Limits
    max_audio_upload_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum audio payload size allowed per recording in bytes (10 MB)",
    )
    max_concurrent_inferences: int = Field(
        default=4,
        description="Maximum concurrent ECAPA-TDNN neural inference operations",
    )
    inference_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for bounded neural inference processing in seconds",
    )

    # Logging, Tracing & Operational Monitoring
    log_format: Literal["console", "json"] = Field(
        default="console",
        description="Logging output format: console (human readable) or json (production structured)",
    )
    log_level: str = Field(default="INFO", description="Standard logging level")
    expose_docs: bool = Field(
        default=True,
        description="Toggle exposure of OpenAPI interactive documentation (/docs, /redoc)",
    )

    # Biometric Vector Encryption (AES-256-GCM)
    # Master key is stored in environment, strictly decoupled from the database.
    biometric_encryption_key: str = Field(
        default="",
        alias="SENTINEL_BIOMETRIC_ENCRYPTION_KEY",
        description="AES-256-GCM master symmetric key (32 bytes base64/hex)",
    )
    biometric_store_path: Path = Field(
        default=Path("outputs/biometric_store"),
        description="Path to store encrypted vector payloads",
    )

    # Authentication & Session Management
    secret_key: str = Field(
        default="sentinel_voice_dev_secret_key_change_in_production_32b",
        alias="SECRET_KEY",
        description="Cryptographic secret for signing JWTs",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(
        default=15,
        description="Access token validity window in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token validity window in days",
    )
    csrf_secret_key: str = Field(
        default="sentinel_voice_csrf_dev_secret_change_in_production",
        alias="CSRF_SECRET_KEY",
        description="CSRF token validation secret",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
        description="Allowed CORS origins list",
    )

    # Audio & Model Engine Parameters
    default_threshold: float = Field(
        default=0.405898,
        description="Phase 5E calibrated baseline threshold seed",
    )
    model_identifier: str = Field(
        default="speechbrain/spkrec-ecapa-voxceleb",
        description="Pretrained ECAPA-TDNN model identifier",
    )
    embedding_dimension: int = Field(
        default=192,
        description="Embedding dimension (ECAPA-TDNN output size)",
    )
    min_audio_duration_sec: float = Field(
        default=1.0,
        description="Minimum audio duration allowed in seconds",
    )
    max_audio_duration_sec: float = Field(
        default=60.0,
        description="Maximum audio duration allowed in seconds",
    )
    sample_rate: int = Field(
        default=16000,
        description="Standard target sampling rate in Hz",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings.

    Returns:
        Settings instance loaded from environment variables and defaults.
    """
    return Settings()

