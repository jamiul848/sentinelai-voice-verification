"""Sentinel Voice - Administrator Console Pydantic Schemas.

Defines serialized API request and response projections for platform overview,
biometric profile inspection, verification analytics, threshold governance,
and audit logging.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------------------
# Platform Overview Schemas
# ------------------------------------------------------------------------------
class UserOverviewStats(BaseModel):
    total: int = Field(..., description="Total registered users")
    active: int = Field(..., description="Active user count")
    inactive: int = Field(..., description="Inactive or suspended user count")


class ProfileOverviewStats(BaseModel):
    total: int = Field(..., description="Total voice profiles")
    active: int = Field(..., description="Active voice profiles")
    revoked: int = Field(..., description="Revoked voice profiles")


class VerificationOverviewStats(BaseModel):
    total: int = Field(..., description="Total verification events evaluated")
    matches: int = Field(..., description="Total authentic MATCH decisions")
    no_matches: int = Field(..., description="Total NO_MATCH decisions")
    match_rate: float = Field(..., description="Percentage of MATCH decisions")
    avg_latency_ms: float = Field(..., description="Average processing latency in ms")


class SystemHealthSummary(BaseModel):
    status: str = Field(..., description="Overall platform status ('ready' or 'unready')")
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    database_status: str = Field(..., description="PostgreSQL connectivity status")
    redis_status: str = Field(..., description="Redis connectivity status")
    model_loaded: bool = Field(..., description="Whether ECAPA-TDNN neural model is loaded")
    encryption_configured: bool = Field(..., description="Whether AES-256-GCM key is configured")


class AuditEventBrief(BaseModel):
    id: uuid.UUID
    action: str
    resource_type: str
    resource_id: str
    actor_user_id: Optional[uuid.UUID] = None
    created_at: datetime


class AdminOverviewResponse(BaseModel):
    users: UserOverviewStats
    voice_profiles: ProfileOverviewStats
    verifications: VerificationOverviewStats
    system_health: SystemHealthSummary
    recent_audit_events: List[AuditEventBrief] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Biometric Profile Management Schemas
# ------------------------------------------------------------------------------
class AdminProfileListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    status: str
    sample_count: int
    mean_pairwise_similarity: float
    model_identifier: str
    created_at: datetime
    updated_at: datetime
    revoked_at: Optional[datetime] = None


class AdminProfileListResponse(BaseModel):
    total: int
    items: List[AdminProfileListItem]


# ------------------------------------------------------------------------------
# Verification Analytics Schemas
# ------------------------------------------------------------------------------
class AdminTimelineItem(BaseModel):
    date: str
    matches: int
    no_matches: int
    total: int
    avg_latency_ms: float


class AdminAnalyticsResponse(BaseModel):
    total_verifications: int
    matches: int
    no_matches: int
    match_rate: float
    no_match_rate: float
    average_latency_ms: float
    timeline: List[AdminTimelineItem] = Field(default_factory=list)
    active_threshold: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------------------
# Threshold Governance Schemas
# ------------------------------------------------------------------------------
class ThresholdConfigRequest(BaseModel):
    version_tag: str = Field(..., min_length=2, max_length=50, description="Unique version tag")
    model_identifier: str = Field(
        default="speechbrain/spkrec-ecapa-voxceleb",
        max_length=100,
        description="Target speaker embedding neural model",
    )
    threshold_value: float = Field(..., ge=-1.0, le=1.0, description="Cosine decision boundary")
    calibration_dataset: str = Field(..., max_length=100, description="Evaluation dataset provenance")
    calibration_criterion: str = Field(
        default="equal_error_rate_minimization",
        max_length=50,
        description="Calibration optimization goal",
    )
    calibration_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Empirical metrics (EER %, trials, ROC-AUC)",
    )
    is_active: bool = Field(default=False, description="Activate upon creation")


class ThresholdConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_tag: str
    model_identifier: str
    threshold_value: float
    calibration_dataset: str
    calibration_criterion: str
    calibration_metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------------------
# Global Audit & Security Event Schemas
# ------------------------------------------------------------------------------
class AdminAuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    changes: Optional[Dict[str, Any]] = None
    created_at: datetime


class AdminAuditLogListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[AdminAuditLogItem]


class AdminSecurityEventsResponse(BaseModel):
    total: int
    events: List[AdminAuditLogItem]
    rate_limiter: Dict[str, Any]

