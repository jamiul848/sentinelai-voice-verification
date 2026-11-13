"""Sentinel Voice - Authentication API Endpoints.

Mounts /api/v1/auth/ routes for registration, login, refresh token rotation, and logout.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from sentinelai.auth.csrf import CSRF_COOKIE_NAME
from sentinelai.auth.dependencies import (
    get_auth_service,
    get_current_user,
    verify_csrf_token,
)
from sentinelai.auth.exceptions import (
    AccountInactiveError,
    AccountTemporarilyThrottledError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordMismatchError,
    TokenExpiredError,
    TokenReusedError,
    WeakPasswordError,
)
from sentinelai.auth.schemas import (
    ApiResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegistrationRequest,
    UserResponse,
)
from sentinelai.auth.service import AuthService
from sentinelai.config import get_settings
from sentinelai.database.models.user import User
from sentinelai.security.rate_limiter import RateLimiter, get_trusted_client_ip

REFRESH_COOKIE_NAME = "sentinel_refresh_token"

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _extract_ip(request: Request) -> Optional[str]:
    """Helper to extract remote client IP address with trusted proxy support."""
    return get_trusted_client_ip(request)


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    dependencies=[Depends(RateLimiter("register", key_type="ip"))],
)
async def register(
    request: Request,
    payload: UserRegistrationRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiResponse[UserResponse]:
    """Register a new user account.

    - Validates email format and uniqueness.
    - Enforces Argon2id password complexity.
    - Automatically assigns standard USER role.
    """
    try:
        user = await auth_service.register_user(payload, ip_address=_extract_ip(request))
        role_names = [r.name for r in user.roles] or ["USER"]
        return ApiResponse(
            success=True,
            message="User registered successfully.",
            data=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                roles=role_names,
                created_at=user.created_at,
            ),
        )
    except EmailAlreadyExistsError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=err.message,
        ) from err
    except (WeakPasswordError, PasswordMismatchError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Authenticate user and issue token pair",
    dependencies=[Depends(RateLimiter("login", key_type="ip"))],
)
async def login(
    request: Request,
    response: Response,
    payload: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """Authenticate with email and password to receive JWT access and refresh tokens.

    Also sets HttpOnly refresh cookie and Double-Submit CSRF cookie.
    """
    try:
        token_data, user = await auth_service.authenticate_user(
            payload,
            ip_address=_extract_ip(request),
        )

        settings = get_settings()
        is_secure = settings.environment == "production"

        # Set HttpOnly refresh token cookie
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=token_data.refresh_token,
            max_age=settings.refresh_token_expire_days * 86400,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            path="/api/v1/auth",
        )

        # Set readable CSRF cookie
        if token_data.csrf_token:
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token_data.csrf_token,
                max_age=settings.refresh_token_expire_days * 86400,
                httponly=False,
                secure=is_secure,
                samesite="lax",
                path="/",
            )

        return ApiResponse(
            success=True,
            message="Login successful.",
            data=token_data,
        )
    except AccountTemporarilyThrottledError as err:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=err.message,
            headers={"Retry-After": str(err.retry_after)},
        ) from err
    except InvalidCredentialsError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except AccountInactiveError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=err.message,
        ) from err


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="Rotate refresh token and issue new token pair",
    dependencies=[Depends(RateLimiter("refresh", key_type="user_or_ip"))],
)
async def refresh(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiResponse[TokenResponse]:
    """Rotate an active refresh token to obtain a fresh access token and refresh token.

    Detects token reuse and invalidates the session family if reuse is detected.
    """
    raw_token = None
    if payload and payload.refresh_token:
        raw_token = payload.refresh_token
    else:
        raw_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required in body or cookie.",
        )

    try:
        token_data = await auth_service.rotate_refresh_token(
            raw_token,
            ip_address=_extract_ip(request),
        )

        settings = get_settings()
        is_secure = settings.environment == "production"

        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=token_data.refresh_token,
            max_age=settings.refresh_token_expire_days * 86400,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            path="/api/v1/auth",
        )

        if token_data.csrf_token:
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=token_data.csrf_token,
                max_age=settings.refresh_token_expire_days * 86400,
                httponly=False,
                secure=is_secure,
                samesite="lax",
                path="/",
            )

        return ApiResponse(
            success=True,
            message="Token refreshed successfully.",
            data=token_data,
        )
    except (TokenExpiredError, InvalidTokenError, TokenReusedError) as err:
        # Clear cookies on failure
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
        response.delete_cookie(CSRF_COOKIE_NAME, path="/")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err.message,
        ) from err
    except AccountInactiveError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=err.message,
        ) from err


@router.post(
    "/logout",
    response_model=ApiResponse[dict],
    summary="Revoke refresh token session and log out",
)
async def logout(
    request: Request,
    response: Response,
    payload: Optional[RefreshTokenRequest] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiResponse[dict]:
    """Revoke refresh token and invalidate authentication cookies.

    Idempotent: safe on repeated invocations.
    """
    raw_token = None
    if payload and payload.refresh_token:
        raw_token = payload.refresh_token
    else:
        raw_token = request.cookies.get(REFRESH_COOKIE_NAME)

    await auth_service.logout_user(
        user=None,
        raw_refresh_token=raw_token,
        ip_address=_extract_ip(request),
    )

    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")

    return ApiResponse(
        success=True,
        message="Logged out successfully.",
        data={"revoked": True},
    )

