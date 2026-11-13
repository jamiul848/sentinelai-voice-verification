"""Sentinel Voice - User Management & Admin API Endpoints.

Mounts:
- /api/v1/users/ (self-service profile and password management)
- /api/v1/admin/users/ (administrative user and RBAC lifecycle controls)
"""

from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from sentinelai.auth.dependencies import (
    get_current_user,
    get_user_service,
    require_admin,
    require_authenticated_user,
)
from sentinelai.auth.exceptions import (
    InvalidCredentialsError,
    LastAdminError,
    PasswordMismatchError,
    SelfModificationError,
    UserNotFoundError,
    WeakPasswordError,
)
from sentinelai.auth.schemas import (
    AdminUpdateRolesRequest,
    AdminUpdateStatusRequest,
    ApiResponse,
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserResponse,
)
from sentinelai.database.models.user import User
from sentinelai.security.rate_limiter import RateLimiter, get_trusted_client_ip
from sentinelai.users.service import UserService

user_router = APIRouter(prefix="/api/v1/users", tags=["User Management"])
admin_router = APIRouter(prefix="/api/v1/admin/users", tags=["Admin User Management"])


def _extract_ip(request: Request) -> Optional[str]:
    return get_trusted_client_ip(request)


# ------------------------------------------------------------------------------
# User Self-Service Endpoints
# ------------------------------------------------------------------------------
@user_router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Get authenticated user profile",
)
async def get_me(
    current_user: User = Depends(require_authenticated_user),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[UserResponse]:
    """Return sanitized profile for the authenticated user."""
    profile = await user_service.get_current_user_profile(current_user)
    return ApiResponse(
        success=True,
        message="Profile retrieved successfully.",
        data=profile,
    )


@user_router.patch(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Update authenticated user profile",
)
async def update_me(
    request: Request,
    payload: UpdateProfileRequest,
    current_user: User = Depends(require_authenticated_user),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[UserResponse]:
    """Update permitted profile attributes (e.g. full name). End-users cannot modify roles or status."""
    updated = await user_service.update_profile(
        current_user,
        payload,
        ip_address=_extract_ip(request),
    )
    return ApiResponse(
        success=True,
        message="Profile updated successfully.",
        data=updated,
    )


@user_router.post(
    "/change-password",
    response_model=ApiResponse[dict],
    summary="Change account password",
    dependencies=[Depends(RateLimiter("password_change", key_type="user"))],
)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: User = Depends(require_authenticated_user),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[dict]:
    """Change account password and revoke all active refresh tokens for this user."""
    try:
        await user_service.change_password(
            current_user,
            payload,
            ip_address=_extract_ip(request),
        )
        return ApiResponse(
            success=True,
            message="Password updated successfully. Existing sessions have been terminated.",
            data={"password_changed": True},
        )
    except InvalidCredentialsError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err.message,
        ) from err
    except (WeakPasswordError, PasswordMismatchError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


# ------------------------------------------------------------------------------
# Administrative User Controls (ADMIN-Only)
# ------------------------------------------------------------------------------
@admin_router.get(
    "",
    response_model=ApiResponse[List[UserResponse]],
    summary="List all users (Admin)",
)
async def admin_list_users(
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    active_only: bool = Query(False, description="Filter for active users only"),
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[List[UserResponse]]:
    """List registered users with pagination and role information."""
    users = await user_service.list_users(skip=skip, limit=limit, active_only=active_only)
    return ApiResponse(
        success=True,
        message=f"Retrieved {len(users)} users.",
        data=users,
    )


@admin_router.get(
    "/{user_id}",
    response_model=ApiResponse[UserResponse],
    summary="Get user details by ID (Admin)",
)
async def admin_get_user(
    user_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[UserResponse]:
    """Fetch user details by UUID primary key."""
    try:
        user = await user_service.get_user_by_id(user_id)
        return ApiResponse(
            success=True,
            message="User retrieved successfully.",
            data=user,
        )
    except UserNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=err.message,
        ) from err


@admin_router.patch(
    "/{user_id}/status",
    response_model=ApiResponse[UserResponse],
    summary="Update user active status (Admin)",
)
async def admin_update_status(
    request: Request,
    user_id: uuid.UUID,
    payload: AdminUpdateStatusRequest,
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[UserResponse]:
    """Activate or deactivate a user account.

    Guards:
    - Administrator cannot deactivate themselves.
    - Last administrator cannot be deactivated.
    """
    try:
        updated = await user_service.update_user_status(
            admin_user=admin_user,
            target_user_id=user_id,
            req=payload,
            ip_address=_extract_ip(request),
        )
        return ApiResponse(
            success=True,
            message="User status updated successfully.",
            data=updated,
        )
    except UserNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message) from err
    except (SelfModificationError, LastAdminError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.message) from err


@admin_router.patch(
    "/{user_id}/roles",
    response_model=ApiResponse[UserResponse],
    summary="Assign user roles (Admin)",
)
async def admin_update_roles(
    request: Request,
    user_id: uuid.UUID,
    payload: AdminUpdateRolesRequest,
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[UserResponse]:
    """Assign explicit RBAC roles to a user account."""
    try:
        updated = await user_service.update_user_roles(
            admin_user=admin_user,
            target_user_id=user_id,
            req=payload,
            ip_address=_extract_ip(request),
        )
        return ApiResponse(
            success=True,
            message="User roles updated successfully.",
            data=updated,
        )
    except UserNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message) from err
    except LastAdminError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.message) from err


@admin_router.delete(
    "/{user_id}",
    response_model=ApiResponse[dict],
    summary="Delete a user account (Admin)",
)
async def admin_delete_user(
    request: Request,
    user_id: uuid.UUID,
    admin_user: User = Depends(require_admin),
    user_service: UserService = Depends(get_user_service),
) -> ApiResponse[dict]:
    """Delete a user account.

    Guards:
    - Administrator cannot delete themselves.
    - Last administrator cannot be deleted.
    """
    try:
        await user_service.delete_user(
            admin_user=admin_user,
            target_user_id=user_id,
            ip_address=_extract_ip(request),
        )
        return ApiResponse(
            success=True,
            message="User deleted successfully.",
            data={"deleted": True},
        )
    except UserNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err.message) from err
    except (SelfModificationError, LastAdminError) as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.message) from err

