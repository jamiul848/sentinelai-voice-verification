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

