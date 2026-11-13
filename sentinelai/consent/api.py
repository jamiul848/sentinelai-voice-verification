"""Sentinel Voice - Biometric Legal Consent API Endpoints.

Mounts /api/v1/consent/ routes for granting, viewing, and revoking voice biometric consent.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Request, status

from sentinelai.auth.dependencies import (
    get_consent_service,
    require_authenticated_user,
)
from sentinelai.auth.schemas import (
    ApiResponse,
    ConsentResponse,
    GrantConsentRequest,
    RevokeConsentRequest,
)
from sentinelai.consent.service import ConsentService
from sentinelai.database.models.user import User

router = APIRouter(prefix="/api/v1/consent", tags=["Biometric Consent"])


def _extract_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None


@router.post(
    "",
    response_model=ApiResponse[ConsentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Grant explicit biometric legal consent",
)
async def grant_consent(
    request: Request,
    payload: GrantConsentRequest,
    current_user: User = Depends(require_authenticated_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ApiResponse[ConsentResponse]:
    """Grant explicit affirmative legal consent for voice biometric enrollment and processing.

    Enforces GDPR and Illinois BIPA compliance.
    """
    record = await consent_service.grant_consent(
        user=current_user,
        req=payload,
        ip_address=_extract_ip(request),
    )
    return ApiResponse(
        success=True,
        message="Biometric consent recorded successfully.",
        data=record,
    )


@router.get(
    "/me",
    response_model=ApiResponse[dict],
    summary="View active consent status and audit history",
)
async def get_my_consent(
    current_user: User = Depends(require_authenticated_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ApiResponse[dict]:
    """Retrieve the caller's active consent status and historical consent timeline."""
    current = await consent_service.get_current_consent(current_user)
    history = await consent_service.get_consent_history(current_user)

    is_active = current is not None and current.consent_granted is True

    return ApiResponse(
        success=True,
        message="Consent status retrieved successfully.",
        data={
            "has_active_consent": is_active,
            "current_consent": current,
            "history": history,
        },
    )


@router.post(
    "/revoke",
    response_model=ApiResponse[ConsentResponse],
    summary="Revoke biometric consent and trigger profile shredding",
)
async def revoke_consent(
    request: Request,
    payload: RevokeConsentRequest,
    current_user: User = Depends(require_authenticated_user),
    consent_service: ConsentService = Depends(get_consent_service),
) -> ApiResponse[ConsentResponse]:
    """Revoke biometric processing consent.

    INVARIANT: Immediately sets voice profiles to REVOKED and executes secure multi-pass
    cryptographic shredding of encrypted embedding files on disk.
    """
    record = await consent_service.revoke_consent(
        user=current_user,
        req=payload,
        ip_address=_extract_ip(request),
    )
    return ApiResponse(
        success=True,
        message="Biometric consent revoked. Voice profiles deactivated and vectors shredded.",
        data=record,
    )

