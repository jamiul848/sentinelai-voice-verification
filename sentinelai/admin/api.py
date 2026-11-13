"""Sentinel Voice - Administrator Operations API Router.

Mounts /api/v1/admin/ operations for platform overview, biometric profiles,
verification analytics, threshold configurations, audit logs, and security telemetry.
All endpoints require ADMIN or SUPER_ADMIN authorization.
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.admin.schemas import (
    AdminAnalyticsResponse,
    AdminAuditLogListResponse,
    AdminOverviewResponse,
    AdminProfileListResponse,
    AdminSecurityEventsResponse,
    ThresholdConfigRequest,
    ThresholdConfigResponse,
)
from sentinelai.admin.service import AdminService
from sentinelai.auth.dependencies import require_admin
from sentinelai.auth.schemas import ApiResponse
from sentinelai.database.connection import get_db_session
from sentinelai.database.models.user import User
from sentinelai.security.rate_limiter import get_trusted_client_ip

router = APIRouter(prefix="/api/v1/admin", tags=["Administrator Operations"])


def _extract_ip(request: Request) -> Optional[str]:
    return get_trusted_client_ip(request)


# ------------------------------------------------------------------------------
# 1. Platform Overview
# ------------------------------------------------------------------------------
@router.get(
    "/overview",
    response_model=ApiResponse[AdminOverviewResponse],
    summary="Platform Telemetry & Operational Overview",
)
async def get_platform_overview(
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AdminOverviewResponse]:
    """Retrieve comprehensive platform metrics, user counts, biometric totals, and operational health."""
    service = AdminService(session)
    data = await service.get_overview()
    return ApiResponse(
        success=True,
        message="Platform overview retrieved successfully.",
        data=data,
    )


# ------------------------------------------------------------------------------
# 2. Biometric Profiles Management
# ------------------------------------------------------------------------------
@router.get(
    "/voice-profiles",
    response_model=ApiResponse[AdminProfileListResponse],
    summary="List Biometric Voice Profiles (Admin)",
)
async def list_voice_profiles(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE or REVOKED"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user UUID"),
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AdminProfileListResponse]:
    """List enrolled voice profile metadata across all platform accounts."""
    service = AdminService(session)
    data = await service.list_voice_profiles(
        skip=skip,
        limit=limit,
        status_filter=status,
        user_id=user_id,
    )
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data.items)} voice profiles.",
        data=data,
    )


@router.post(
    "/voice-profiles/{profile_id}/revoke",
    response_model=ApiResponse[dict],
    summary="Revoke Voice Profile & Shred Vector (Admin)",
)
async def admin_revoke_voice_profile(
    request: Request,
    profile_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[dict]:
    """Admin-initiated revocation with immediate NIST SP 800-88 vector shredding."""
    service = AdminService(session)
    res = await service.revoke_voice_profile(
        profile_id=profile_id,
        admin_user=admin_user,
        ip_address=_extract_ip(request),
    )
    return ApiResponse(
        success=True,
        message="Voice profile revoked and vector shredded successfully.",
        data=res,
    )


# ------------------------------------------------------------------------------
# 3. Verification Analytics
# ------------------------------------------------------------------------------
@router.get(
    "/analytics",
    response_model=ApiResponse[AdminAnalyticsResponse],
    summary="Speaker Verification Analytics & Decision Volumes",
)
async def get_verification_analytics(
    days: int = Query(7, ge=1, le=90, description="Analysis historical window in days"),
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AdminAnalyticsResponse]:
    """Calculate aggregate verification volumes, match rates, and latencies from immutable event logs."""
    service = AdminService(session)
    data = await service.get_analytics(days=days)
    return ApiResponse(
        success=True,
        message="Verification analytics retrieved successfully.",
        data=data,
    )


# ------------------------------------------------------------------------------
# 4. Threshold Governance
# ------------------------------------------------------------------------------
@router.get(
    "/thresholds",
    response_model=ApiResponse[List[ThresholdConfigResponse]],
    summary="List Calibrated Threshold Configurations (Admin)",
)
async def list_threshold_configurations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[List[ThresholdConfigResponse]]:
    """List registered decision boundaries with calibration provenance."""
    service = AdminService(session)
    data = await service.list_thresholds(skip=skip, limit=limit)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data)} threshold configurations.",
        data=data,
    )


@router.get(
    "/thresholds/active",
    response_model=ApiResponse[Optional[ThresholdConfigResponse]],
    summary="Get Current Active Decision Threshold (Admin)",
)
async def get_active_threshold(
    model_identifier: str = Query("speechbrain/spkrec-ecapa-voxceleb"),
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[Optional[ThresholdConfigResponse]]:
    """Fetch currently active operating threshold for the neural backbone."""
    service = AdminService(session)
    data = await service.get_active_threshold(model_identifier=model_identifier)
    return ApiResponse(
        success=True,
        message="Active threshold configuration retrieved.",
        data=data,
    )


@router.post(
    "/thresholds",
    response_model=ApiResponse[ThresholdConfigResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register New Calibrated Threshold (Admin)",
)
async def create_threshold_configuration(
    request: Request,
    payload: ThresholdConfigRequest,
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ThresholdConfigResponse]:
    """Register a new calibrated decision threshold with empirical provenance."""
    service = AdminService(session)
    data = await service.create_threshold(
        req=payload,
        admin_user=admin_user,
        ip_address=_extract_ip(request),
    )
    return ApiResponse(
        success=True,
        message="Threshold configuration registered successfully.",
        data=data,
    )


@router.post(
    "/thresholds/{threshold_id}/activate",
    response_model=ApiResponse[ThresholdConfigResponse],
    summary="Activate Operating Threshold (Admin)",
)
async def activate_threshold_configuration(
    request: Request,
    threshold_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ThresholdConfigResponse]:
    """Set specified threshold as the active operating boundary, deactivating prior configurations."""
    service = AdminService(session)
    data = await service.activate_threshold(
        threshold_id=threshold_id,
        admin_user=admin_user,
        ip_address=_extract_ip(request),
    )
    return ApiResponse(
        success=True,
        message=f"Threshold configuration {data.version_tag} successfully activated.",
        data=data,
    )


# ------------------------------------------------------------------------------
# 5. Global Audit Logs
# ------------------------------------------------------------------------------
@router.get(
    "/audit-logs",
    response_model=ApiResponse[AdminAuditLogListResponse],
    summary="Query Global Immutable Audit Logs (Admin)",
)
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None, description="Filter by event action (e.g. USER_REGISTERED)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (e.g. user)"),
    actor_user_id: Optional[uuid.UUID] = Query(None, description="Filter by actor UUID"),
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AdminAuditLogListResponse]:
    """Retrieve immutable audit event trail with pagination and parameter filtering."""
    service = AdminService(session)
    data = await service.list_audit_logs(
        skip=skip,
        limit=limit,
        action=action,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
    )
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(data.items)} audit logs.",
        data=data,
    )


# ------------------------------------------------------------------------------
# 6. Security Events & Rate Limiter Telemetry
# ------------------------------------------------------------------------------
@router.get(
    "/security-events",
    response_model=ApiResponse[AdminSecurityEventsResponse],
    summary="Security Event Audit & Rate Limiting Telemetry (Admin)",
)
async def get_security_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[AdminSecurityEventsResponse]:
    """Retrieve filtered security incidents, privilege mutations, and active rate limiting rules."""
    service = AdminService(session)
    data = await service.get_security_events(skip=skip, limit=limit)
    return ApiResponse(
        success=True,
        message="Security events and telemetry retrieved successfully.",
        data=data,
    )

