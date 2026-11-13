"""Sentinel Voice - Biometric Pipeline FastAPI Router.

Exposes authenticated endpoints for:
- Voiceprint enrollment (multi-sample centroid aggregation, AES-256-GCM envelope encryption).
- Voice verification (single probe inference, cosine similarity, dynamic thresholding).
- Voice profile lifecycle management (active profile inspection, history, re-enrollment, revocation).
- Verification audit trail exploration (paginated, filtered event queries).
"""

from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.auth.dependencies import require_authenticated_user
from sentinelai.biometrics.enrollment_service import BiometricEnrollmentService
from sentinelai.biometrics.profile_service import BiometricProfileService
from sentinelai.biometrics.schemas import (
    EnrollmentResponse,
    ProfileRevocationResponse,
    ReEnrollmentResponse,
    VerificationHistoryResponse,
    VerificationResponse,
    VoiceProfileDetailResponse,
    VoiceProfileResponse,
)
from sentinelai.biometrics.verification_service import BiometricVerificationService
from sentinelai.database.connection import get_db_session
from sentinelai.database.models.user import User
from sentinelai.security.rate_limiter import RateLimiter, get_trusted_client_ip

router = APIRouter(prefix="/api/v1/biometrics", tags=["Biometrics"])


def _extract_client_ip(request: Request) -> Optional[str]:
    """Helper resolving client IP address safely with trusted proxy support."""
    return get_trusted_client_ip(request)


@router.post(
    "/enroll",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll Voiceprint",
    description="Aggregate 3 to 10 audio recordings into an encrypted reference centroid profile.",
    dependencies=[Depends(RateLimiter("enrollment", key_type="user"))],
)
async def enroll_voiceprint(
    request: Request,
    files: List[UploadFile] = File(
        ...,
        description="Multiple audio files (WAV or FLAC, minimum 3, 1-60 sec each)",
    ),
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> EnrollmentResponse:
    """Enroll a user voiceprint using multi-sample ECAPA-TDNN extraction."""
    service = BiometricEnrollmentService(session)
    client_ip = _extract_client_ip(request)
    return await service.enroll_user(
        user=current_user,
        audio_files=files,
        allow_replace=False,
        client_ip=client_ip,
    )


@router.post(
    "/verify",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Speaker Voice",
    description="Submit a probe voice recording to verify identity against the enrolled voiceprint.",
    dependencies=[Depends(RateLimiter("verification", key_type="user"))],
)
async def verify_speaker(
    request: Request,
    file: UploadFile = File(..., description="Probe audio recording (WAV or FLAC, 1-60 sec)"),
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> VerificationResponse:
    """Verify probe audio against user's active enrolled profile."""
    service = BiometricVerificationService(session)
    client_ip = _extract_client_ip(request)
    return await service.verify_user(
        user=current_user,
        audio_file=file,
        client_ip=client_ip,
    )


@router.get(
    "/profile",
    response_model=VoiceProfileDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Voice Profile",
    description="Retrieve the caller's active voice profile and acoustic sample metadata.",
)
async def get_active_profile(
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> VoiceProfileDetailResponse:
    """Fetch active voice profile for the authenticated caller."""
    service = BiometricProfileService(session)
    return await service.get_active_profile(current_user.id)


@router.get(
    "/profile/history",
    response_model=List[VoiceProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="List Voice Profile History",
    description="List all historical active and revoked profiles for the caller.",
)
async def list_profile_history(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> List[VoiceProfileResponse]:
    """Fetch profile version history for the caller."""
    service = BiometricProfileService(session)
    return await service.get_profile_history(current_user.id, skip=skip, limit=limit)


@router.post(
    "/profile/re-enroll",
    response_model=ReEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Re-enroll Voiceprint",
    description="Deactivate previous profile, shred old vector container, and enroll new voiceprint.",
    dependencies=[Depends(RateLimiter("enrollment", key_type="user"))],
)
async def re_enroll_voiceprint(
    request: Request,
    files: List[UploadFile] = File(..., description="New enrollment audio recordings (3 to 10 files)"),
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> ReEnrollmentResponse:
    """Re-enroll caller's voiceprint, shredding the prior encrypted vector container."""
    service = BiometricProfileService(session)
    client_ip = _extract_client_ip(request)
    return await service.re_enroll(
        user=current_user,
        audio_files=files,
        client_ip=client_ip,
    )


@router.delete(
    "/profile",
    response_model=ProfileRevocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke Voice Profile",
    description="Revoke the active profile and cryptographically shred the vector container.",
)
async def revoke_active_profile(
    request: Request,
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> ProfileRevocationResponse:
    """Revoke active voice profile and shred stored biometric vectors."""
    service = BiometricProfileService(session)
    client_ip = _extract_client_ip(request)
    return await service.revoke_profile(current_user, client_ip=client_ip)


@router.get(
    "/verification-history",
    response_model=VerificationHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List Verification History",
    description="Query chronological, filterable verification transaction events for the caller.",
)
async def get_verification_history(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    decision: Optional[str] = Query(None, description="Filter by decision: MATCH or NO_MATCH"),
    start_date: Optional[datetime] = Query(None, description="Earliest event timestamp (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Latest event timestamp (ISO 8601)"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"),
    current_user: User = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
) -> VerificationHistoryResponse:
    """Fetch paginated verification history for the caller."""
    service = BiometricProfileService(session)
    return await service.get_verification_history(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        decision=decision,
        start_date=start_date,
        end_date=end_date,
        order=order,
    )
