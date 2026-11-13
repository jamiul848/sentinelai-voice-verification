"""FastAPI Router for Speaker Verification.

Provides endpoints for 1:1 speaker identity verification against enrolled reference
profiles and service health diagnostics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status

from sentinelai.verification.config import VerificationConfig
from sentinelai.verification.exceptions import (
    InvalidAudioInputError,
    ProfileNotFoundError,
    ProfileRevokedError,
    ThresholdValidationError,
    UnauthorizedVerificationError,
    VerificationError,
    VerificationScoringError,
)
from sentinelai.verification.schemas import (
    VerificationHealthResponse,
    VerificationResponse,
)
from sentinelai.verification.service import SpeakerVerificationService

HTTP_413_PAYLOAD_TOO_LARGE = (
    status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413
)

router = APIRouter(prefix="/verification", tags=["Speaker Verification"])

# Singleton service instance (overridable for testing)
_verification_service: Optional[SpeakerVerificationService] = None


def get_verification_service() -> SpeakerVerificationService:
    """Dependency provider for SpeakerVerificationService."""
    global _verification_service
    if _verification_service is None:
        _verification_service = SpeakerVerificationService()
    return _verification_service


def verify_authorization_hook(
    authorization: Optional[str] = Header(
        None,
        description="Authorization credential header (hook for OAuth2/JWT middleware in production).",
    ),
) -> None:
    """Authorization hook for verification requests.

    SECURITY ARCHITECTURAL NOTE:
        In production systems, knowing a user_id or profile_id is NEVER sufficient
        authorization. This hook provides the dependency injection point for validating
        authenticated session tokens or API keys before proceeding with biometric comparison.
    """
    pass


@router.post(
    "/verify",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify speaker identity against an enrolled profile",
    description=(
        "Performs 1:1 speaker verification comparing a submitted audio recording against "
        "an active enrolled reference voiceprint. Returns MATCH or NO_MATCH."
    ),
)
async def verify_speaker(
    audio_file: UploadFile = File(..., description="WAV voice recording of the claimant speaker."),
    user_id: Optional[str] = Form(None, description="Claimed user identifier."),
    profile_id: Optional[str] = Form(None, description="Enrolled reference profile identifier."),
    service: SpeakerVerificationService = Depends(get_verification_service),
    _auth: None = Depends(verify_authorization_hook),
) -> VerificationResponse:
    """Verify a claimant's voice against an enrolled speaker profile."""
    if not user_id and not profile_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'user_id' or 'profile_id' must be provided.",
        )

    if not audio_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file must have a valid filename.",
        )

    # Read and enforce file upload limits
    audio_bytes = await audio_file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded audio file '{audio_file.filename}' is empty (0 bytes).",
        )

    if len(audio_bytes) > service.config.max_audio_size_bytes:
        raise HTTPException(
            status_code=HTTP_413_PAYLOAD_TOO_LARGE,
            detail=(
                f"Audio file '{audio_file.filename}' ({len(audio_bytes)} bytes) exceeds "
                f"maximum allowed upload size of {service.config.max_audio_size_bytes} bytes."
            ),
        )

    try:
        response = service.verify_speaker(
            audio_input=audio_bytes,
            user_id=user_id,
            profile_id=profile_id,
            request_metadata={"filename": audio_file.filename},
        )
        return response

    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ProfileRevokedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except InvalidAudioInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except VerificationScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except UnauthorizedVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal verification error: {exc}",
        ) from exc


@router.get(
    "/health",
    response_model=VerificationHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check verification engine health status",
    description="Returns service health, active device, and threshold version without exposing biometrics.",
)
async def verification_health(
    service: SpeakerVerificationService = Depends(get_verification_service),
) -> VerificationHealthResponse:
    """Diagnostic health check for the speaker verification engine."""
    model_loaded = False
    device = "cpu"
    try:
        model_loader = getattr(service.extractor, "loader", None)
        if model_loader is not None:
            model_loaded = model_loader.is_loaded
            if hasattr(model_loader, "get_device"):
                device = str(model_loader.get_device())
            elif hasattr(model_loader, "config"):
                device = str(getattr(model_loader.config, "resolved_device", "cpu"))
    except Exception:
        pass

    return VerificationHealthResponse(
        status="healthy",
        service="SentinelAI Speaker Verification Engine",
        model_loaded=model_loaded,
        device=device,
        threshold_version=service.threshold.version,
    )
