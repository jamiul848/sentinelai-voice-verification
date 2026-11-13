"""Pydantic schemas and domain data models for voice enrollment and speaker profiles."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field


class ProfileStatus(str, Enum):
    """Lifecycle status of a speaker profile."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class UserEnrollmentStatus(str, Enum):
    """High-level enrollment state for a given user identifier."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    NOT_ENROLLED = "NOT_ENROLLED"


class SpeakerProfile(BaseModel):
    """Domain model representing an enrolled speaker voiceprint profile.

    Biometric Note:
        The reference_embedding and individual_embeddings arrays contain sensitive
        numerical voiceprint vectors and are NEVER exposed in public API representations.
    """

    model_config = {"arbitrary_types_allowed": True}

    profile_id: str = Field(..., description="Unique profile identifier (UUID4).")
    user_id: str = Field(..., description="Unique identifier of the enrolled user.")
    reference_embedding: Optional[np.ndarray] = Field(
        default=None,
        description="L2-normalized reference centroid embedding vector.",
    )
    individual_embeddings: Optional[List[np.ndarray]] = Field(
        default=None,
        description="Optional list of individual utterance embedding vectors for audit/variance.",
    )
    embedding_dimension: int = Field(..., gt=0, description="Dimensionality of the embedding vector.")
    model_name: str = Field(..., description="Name or identifier of the ECAPA-TDNN model used.")
    model_version: Optional[str] = Field(default=None, description="Model checkpoint or revision identifier.")
    enrollment_sample_count: int = Field(..., ge=1, description="Number of audio recordings used for enrollment.")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Profile creation timestamp (UTC).",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Profile last update timestamp (UTC).",
    )
    consent_status: bool = Field(..., description="Whether user provided explicit biometric consent.")
    profile_status: ProfileStatus = Field(
        default=ProfileStatus.ACTIVE,
        description="Current operational status (ACTIVE or REVOKED).",
    )
    revoked_at: Optional[datetime] = Field(default=None, description="Timestamp of revocation if revoked.")
    revocation_reason: Optional[str] = Field(default=None, description="Reason for profile revocation.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata and metrics.")

    @property
    def is_active(self) -> bool:
        """Check if profile is currently active."""
        return self.profile_status == ProfileStatus.ACTIVE

    def to_public(self) -> "SpeakerProfilePublic":
        """Generate a safe public view that strictly omits biometric vectors."""
        return SpeakerProfilePublic(
            profile_id=self.profile_id,
            user_id=self.user_id,
            status=self.profile_status,
            enrollment_sample_count=self.enrollment_sample_count,
            embedding_dimension=self.embedding_dimension,
            model_name=self.model_name,
            created_at=self.created_at.isoformat(),
            updated_at=self.updated_at.isoformat(),
            consent_status=self.consent_status,
            metadata=self.metadata,
        )


# -----------------------------------------------------------------------------
# Public API Response Schemas (Strictly no biometric embeddings)
# -----------------------------------------------------------------------------


class SpeakerProfilePublic(BaseModel):
    """Public representation of an enrolled speaker profile (safe for API responses)."""

    profile_id: str
    user_id: str
    status: ProfileStatus
    enrollment_sample_count: int
    embedding_dimension: int
    model_name: str
    created_at: str
    updated_at: str
    consent_status: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EnrollmentResponse(BaseModel):
    """API response model returned upon successful speaker registration."""

    success: bool = True
    profile_id: str
    user_id: str
    sample_count: int
    embedding_dimension: int
    created_at: str
    message: str = "Voice profile successfully enrolled."


class ReEnrollmentResponse(BaseModel):
    """API response model returned upon successful re-enrollment."""

    success: bool = True
    profile_id: str
    previous_profile_id: str
    user_id: str
    sample_count: int
    embedding_dimension: int
    updated_at: str
    message: str = "Voice profile successfully updated and previous profile superseded."


class RevocationResponse(BaseModel):
    """API response model returned upon profile revocation."""

    success: bool = True
    profile_id: str
    user_id: str
    status: ProfileStatus = ProfileStatus.REVOKED
    revoked_at: str
    reason: Optional[str] = None
    message: str = "Voice profile revoked and biometric vectors purged."


class EnrollmentStatusResponse(BaseModel):
    """API response model for checking enrollment state of a user."""

    user_id: str
    status: UserEnrollmentStatus
    profile_id: Optional[str] = None
    sample_count: Optional[int] = None
    updated_at: Optional[str] = None

