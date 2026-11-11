"""Configuration settings for the SentinelAI Speaker Verification engine."""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from sentinelai.verification.threshold import VerificationThreshold


class VerificationConfig(BaseModel):
    """Configuration model for the Speaker Verification pipeline."""

    threshold_value: float = Field(
        default=VerificationThreshold.DEFAULT_DEV_THRESHOLD,
        ge=VerificationThreshold.MIN_THRESHOLD,
        le=VerificationThreshold.MAX_THRESHOLD,
        description="Decision threshold for cosine similarity score. A score >= threshold_value is a MATCH.",
    )
    threshold_version: str = Field(
        default=VerificationThreshold.DEFAULT_DEV_VERSION,
        description="Version identifier for the active threshold.",
    )
    expose_similarity_score: bool = Field(
        default=True,
        description="Whether to expose the raw numerical similarity score in public responses.",
    )
    max_audio_size_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        gt=0,
        description="Maximum permitted audio upload size in bytes.",
    )
    storage_dir: Path = Field(
        default=Path("data/profiles"),
        description="Directory containing enrolled speaker profile records.",
    )
    audit_log_path: Optional[Path] = Field(
        default=Path("data/audit/verification_audit.jsonl"),
        description="Filesystem path for append-only verification audit logs.",
    )

    @field_validator("storage_dir", "audit_log_path", mode="before")
    @classmethod
    def convert_to_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Convert string path inputs to Path instances."""
        if v is None:
            return None
        return Path(v)

