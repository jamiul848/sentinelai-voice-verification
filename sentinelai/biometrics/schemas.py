"""Sentinel Voice - Biometric Pipeline API Request & Response Schemas.

Pydantic models governing voice enrollment, probe verification, profile state,
and verification audit log representations.
"""

from datetime import datetime
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class EnrollmentSampleMetadata(BaseModel):
    """Numerical acoustic metrics for an individual enrollment utterance."""

    model_config = ConfigDict(from_attributes=True)

    duration_sec: float = Field(..., description="Duration in seconds")
    rms_energy: float = Field(..., description="Root-mean-square acoustic energy")
    peak_amplitude: float = Field(..., description="Peak absolute sample amplitude")
    audio_format: str = Field(..., description="Acoustic container format (WAV or FLAC)")
    snr_db: Optional[float] = Field(None, description="Signal-to-noise ratio in decibels")


class EnrollmentResponse(BaseModel):
    """Structured response returned upon successful voice enrollment."""

    model_config = ConfigDict(from_attributes=True)

    profile_id: uuid.UUID = Field(..., description="Unique voice profile identifier")
    user_id: uuid.UUID = Field(..., description="Owning user UUID")
    status: str = Field(..., description="Profile lifecycle status (ACTIVE, REVOKED)")
    sample_count: int = Field(..., description="Number of speech recordings aggregated")
    mean_pairwise_similarity: float = Field(..., description="Intra-session cosine consistency score")
    model_identifier: str = Field(..., description="Speaker recognition neural backbone")
    created_at: datetime = Field(..., description="Profile creation UTC timestamp")
    samples: List[EnrollmentSampleMetadata] = Field(default_factory=list, description="Acoustic metrics per sample")


class VerificationResponse(BaseModel):
    """Structured response returned from live speaker verification evaluation."""

    model_config = ConfigDict(from_attributes=True)

    verification_id: uuid.UUID = Field(..., description="Immutable verification transaction UUID")
    decision: str = Field(..., description="Binary decision: MATCH or NO_MATCH")
    is_match: bool = Field(..., description="Boolean verification outcome")
    similarity_score: float = Field(..., description="Cosine similarity between probe and reference [-1, 1]")
    applied_threshold: float = Field(..., description="Calibrated operational decision threshold applied")
    processing_time_ms: float = Field(..., description="End-to-end inference and evaluation latency in milliseconds")
    model_identifier: str = Field(..., description="Neural model identifier used for verification")
    threshold_version: Optional[str] = Field(None, description="Calibration version tag of applied threshold")
    threshold_id: Optional[uuid.UUID] = Field(None, description="UUID of threshold configuration record")
    timestamp: datetime = Field(..., description="Verification execution timestamp")


class VoiceProfileResponse(BaseModel):
    """Voice profile summary metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Profile UUID")
    user_id: uuid.UUID = Field(..., description="User UUID")
    status: str = Field(..., description="Lifecycle status (ACTIVE, REVOKED)")
    sample_count: int = Field(..., description="Number of enrolled samples")
    mean_pairwise_similarity: float = Field(..., description="Internal centroid consistency score")
    model_identifier: str = Field(..., description="Model identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp if revoked")


class VoiceProfileDetailResponse(VoiceProfileResponse):
    """Voice profile metadata including constituent enrollment sample records."""

    enrollment_records: List[EnrollmentSampleMetadata] = Field(
        default_factory=list,
        description="Acoustic metadata for individual enrollment recordings",
    )


class VerificationHistoryItem(BaseModel):
    """Individual verification transaction entry in user history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Event UUID")
    decision: str = Field(..., description="MATCH or NO_MATCH")
    is_match: bool = Field(..., description="Verification result")
    similarity_score: float = Field(..., description="Observed cosine similarity")
    applied_threshold: float = Field(..., description="Applied threshold")
    processing_time_ms: float = Field(..., description="Processing latency in ms")
    created_at: datetime = Field(..., description="Event timestamp")
    threshold_id: Optional[uuid.UUID] = Field(None, description="Threshold configuration UUID")
    client_ip: Optional[str] = Field(None, description="Client IP address")


class VerificationHistoryResponse(BaseModel):
    """Paginated collection of verification audit events."""

    total: int = Field(..., description="Total matching verification records")
    skip: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Page size limit")
    items: List[VerificationHistoryItem] = Field(default_factory=list, description="Verification events")


class ReEnrollmentResponse(BaseModel):
    """Response returned when successfully re-enrolling a voiceprint."""

    profile_id: uuid.UUID = Field(..., description="New active profile UUID")
    previous_profile_id: Optional[uuid.UUID] = Field(None, description="Deactivated profile UUID")
    status: str = Field("ACTIVE", description="New profile status")
    sample_count: int = Field(..., description="Number of samples aggregated")
    mean_pairwise_similarity: float = Field(..., description="Centroid consistency")
    message: str = Field(
        "Voiceprint re-enrollment successful. Previous profile was revoked and shredded.",
        description="Status message",
    )


class ProfileRevocationResponse(BaseModel):
    """Response returned upon explicit voice profile revocation."""

    profile_id: uuid.UUID = Field(..., description="Revoked profile UUID")
    status: str = Field("REVOKED", description="Profile status")
    revoked_at: datetime = Field(..., description="Revocation timestamp")
    message: str = Field(
        "Voice profile revoked and biometric vector shredded from storage.",
        description="Status message",
    )

