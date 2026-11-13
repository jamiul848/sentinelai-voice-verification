"""FastAPI Router for Voice Enrollment and Speaker Profile Management.

Provides endpoints for registering voiceprints, re-enrollment, status checking,
profile inspection, and revocation.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status

from sentinelai.enrollment.config import EnrollmentConfig
from sentinelai.enrollment.exceptions import (
    DuplicateEnrollmentError,
    EnrollmentConsentError,
    EnrollmentValidationError,
    ExcessiveRecordingsError,
    InsufficientRecordingsError,
    ProfileNotFoundError,
    ProfileRevokedError,
)
from sentinelai.enrollment.schemas import (
    EnrollmentResponse,
    EnrollmentStatusResponse,
    ReEnrollmentResponse,
    RevocationResponse,
    SpeakerProfilePublic,
)
from sentinelai.enrollment.service import EnrollmentService

router = APIRouter(prefix="/enrollment", tags=["Voice Enrollment"])

# Default singleton service instance (can be overridden via dependency injection)
_enrollment_service: Optional[EnrollmentService] = None


def get_enrollment_service() -> EnrollmentService:
    """Dependency provider for EnrollmentService."""
    global _enrollment_service
    if _enrollment_service is None:
        _enrollment_service = EnrollmentService()
    return _enrollment_service


def verify_authorization_hook(
    authorization: Optional[str] = Header(None, description="Authorization token header (hook for auth middleware)"),
) -> None:
    """Authorization hook for profile administration operations.

    Security Notice:
        In production, this hook must validate JWT tokens, mTLS, or API keys.
        User IDs alone do NOT provide authentication or authorization.
    """
    # Research prototype accepts requests but documents the security requirement
    pass


async def _read_and_validate_uploads(files: List[UploadFile], config: EnrollmentConfig) -> List[bytes]:
    """Read upload contents into memory while enforcing max file size limits."""
    file_bytes_list: List[bytes] = []

    for file in files:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All uploaded files must have valid filenames.",
            )
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' is empty (0 bytes).",
            )
        if len(content) > config.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{file.filename}' exceeds maximum allowed size of {config.max_file_size_bytes} bytes.",
            )
        file_bytes_list.append(content)

    return file_bytes_list


@router.post(
    "/register",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a new speaker voice profile",
    description="Accepts multiple voice recordings and user consent to create an enrolled reference voiceprint.",
)
async def register_speaker(
    user_id: str = Form(..., description="Unique user identifier for enrollment"),
    consent: bool = Form(..., description="Explicit biometric consent flag (must be True)"),
    files: List[UploadFile] = File(..., description="At least 3 valid WAV audio recordings"),
    service: EnrollmentService = Depends(get_enrollment_service),
) -> EnrollmentResponse:
    """Enroll a new speaker voice profile."""
    audio_bytes = await _read_and_validate_uploads(files, service.config)

    try:
        response = service.enroll(
            user_id=user_id,
            audio_sources=audio_bytes,
            consent=consent,
        )
        return response
    except EnrollmentConsentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DuplicateEnrollmentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except (InsufficientRecordingsError, ExcessiveRecordingsError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except EnrollmentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrollment failure: {exc}",
        )


@router.get(
    "/profile/{profile_id}",
    response_model=SpeakerProfilePublic,
    status_code=status.HTTP_200_OK,
    summary="Retrieve an enrolled speaker profile",
    description="Returns public metadata of an enrolled profile. Biometric embeddings are strictly omitted.",
)
async def get_speaker_profile(
    profile_id: str,
    service: EnrollmentService = Depends(get_enrollment_service),
) -> SpeakerProfilePublic:
    """Retrieve public profile metadata by profile ID."""
    try:
        return service.get_public_profile(profile_id)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get(
    "/status/{user_id}",
    response_model=EnrollmentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Check enrollment status for a user ID",
    description="Reports whether a user profile is ACTIVE, REVOKED, or NOT_ENROLLED.",
)
async def check_user_status(
    user_id: str,
    service: EnrollmentService = Depends(get_enrollment_service),
) -> EnrollmentStatusResponse:
    """Check enrollment status of a user."""
    try:
        return service.get_enrollment_status(user_id)
    except EnrollmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/reenroll",
    response_model=ReEnrollmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Re-enroll an existing speaker",
    description="Updates a user's voiceprint, revoking and purging the previous reference embedding.",
)
async def reenroll_speaker(
    user_id: str = Form(..., description="Unique user identifier for re-enrollment"),
    consent: bool = Form(..., description="Explicit biometric consent flag"),
    files: List[UploadFile] = File(..., description="New set of audio recordings"),
    service: EnrollmentService = Depends(get_enrollment_service),
    _auth: None = Depends(verify_authorization_hook),
) -> ReEnrollmentResponse:
    """Re-enroll a speaker with new voice samples."""
    audio_bytes = await _read_and_validate_uploads(files, service.config)

    try:
        response = service.re_enroll(
            user_id=user_id,
            audio_sources=audio_bytes,
            consent=consent,
        )
        return response
    except EnrollmentConsentError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except (InsufficientRecordingsError, ExcessiveRecordingsError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except EnrollmentValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-enrollment failure: {exc}",
        )


@router.delete(
    "/profile/{profile_id}",
    response_model=RevocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke a speaker voice profile",
    description="Revokes profile and permanently purges stored biometric embeddings.",
)
async def revoke_profile(
    profile_id: str,
    reason: Optional[str] = Query(None, description="Optional revocation justification"),
    service: EnrollmentService = Depends(get_enrollment_service),
    _auth: None = Depends(verify_authorization_hook),
) -> RevocationResponse:
    """Revoke profile and purge biometric embeddings."""
    try:
        return service.revoke_profile(profile_id, reason=reason)
    except ProfileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
