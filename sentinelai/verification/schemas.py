"""Pydantic schemas and domain data models for speaker verification."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    """Categorical outcome of a speaker verification attempt."""

    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_REVOKED = "PROFILE_REVOKED"
    INVALID_AUDIO = "INVALID_AUDIO"
    VERIFICATION_ERROR = "VERIFICATION_ERROR"


class VerificationResponse(BaseModel):
    """Safe public response schema for speaker verification outcomes.

    BIOMETRIC PRIVACY SAFEGUARD:
        This response intentionally withholds all raw audio bytes, extracted embedding
        vectors, reference tensors, and filesystem storage paths. The similarity score
        is optional and only included if score exposure is explicitly enabled in config.
    """

    verification_id: str = Field(..., description="Unique verification attempt identifier (UUID4).")
    user_id: str = Field(..., description="Claimed user identifier.")
    profile_id: str = Field(..., description="Enrolled reference profile identifier.")
    status: VerificationStatus = Field(..., description="Categorical outcome of the verification.")
    verified: bool = Field(..., description="Boolean verification decision (True if MATCH, else False).")
    similarity_score: Optional[float] = Field(
        default=None,
        description="Raw cosine similarity score in [-1.0, 1.0]. Null if score exposure is disabled.",
    )
    threshold_version: str = Field(..., description="Version identifier of the decision threshold used.")
    model_name: str = Field(..., description="Pretrained speaker recognition model identifier.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of the verification event.",
    )
    processing_time_ms: float = Field(..., ge=0.0, description="Total pipeline latency in milliseconds.")
    message: str = Field(..., description="Human-readable outcome description.")


class VerificationHealthResponse(BaseModel):
    """Service health and diagnostic status."""

    status: str = Field(..., description="Service health state (e.g., 'healthy').")
    service: str = Field(default="SentinelAI Speaker Verification Engine")
    model_loaded: bool = Field(..., description="Whether ECAPA-TDNN model is loaded in memory.")
    device: str = Field(..., description="Active compute device ('cpu' or 'cuda').")
    threshold_version: str = Field(..., description="Current active verification threshold version.")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

