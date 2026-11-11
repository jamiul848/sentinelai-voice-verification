"""Configuration settings for voice enrollment and speaker profile storage."""

from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator


class EnrollmentConfig(BaseModel):
    """Configuration settings for voice enrollment, recording quotas, and storage.

    Attributes:
        min_recordings: Minimum number of valid audio recordings required for enrollment.
        max_recordings: Maximum number of audio recordings permitted in a single enrollment.
        max_file_size_bytes: Maximum acceptable byte size per uploaded audio file.
        storage_dir: Directory where profile metadata and biometric reference vectors are stored.
        retain_individual_embeddings: Whether to store individual utterance embeddings alongside the reference vector.
        require_explicit_consent: Whether enrollment strictly requires positive consent flag.
        purge_biometrics_on_revocation: Whether revoking a profile deletes the stored biometric vectors.
    """

    min_recordings: int = Field(
        default=3,
        ge=1,
        description="Minimum number of valid voice recordings required to build a reference profile.",
    )
    max_recordings: int = Field(
        default=10,
        gt=1,
        description="Maximum number of voice recordings permitted in a single enrollment request.",
    )
    max_file_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
        description="Maximum allowed size per uploaded audio file in bytes (default: 10 MB).",
    )
    storage_dir: Path = Field(
        default=Path(".cache/sentinelai/profiles"),
        description="Filesystem directory for storing speaker profiles and reference embeddings.",
    )
    retain_individual_embeddings: bool = Field(
        default=True,
        description="Store separate utterance embeddings for research variance analysis.",
    )
    require_explicit_consent: bool = Field(
        default=True,
        description="Enforce positive biometric consent confirmation upon registration.",
    )
    purge_biometrics_on_revocation: bool = Field(
        default=True,
        description="Erase biometric embedding data upon profile revocation.",
    )

    @field_validator("storage_dir", mode="before")
    @classmethod
    def convert_storage_dir_to_path(cls, v: object) -> Path:
        """Ensure storage_dir is a pathlib.Path."""
        if isinstance(v, str):
            return Path(v)
        return v  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_recording_bounds(self) -> "EnrollmentConfig":
        """Validate that min_recordings is strictly less than or equal to max_recordings."""
        if self.min_recordings > self.max_recordings:
            raise ValueError(
                f"min_recordings ({self.min_recordings}) cannot exceed max_recordings ({self.max_recordings})."
            )
        return self

