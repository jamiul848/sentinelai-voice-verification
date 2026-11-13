"""Sentinel Voice - Authentication & RBAC FastAPI Route Dependencies.

Provides secure token resolution, role-based authorization guards, and database service injection.
"""

from typing import Callable, List, Optional
import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.auth.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME, validate_double_submit_csrf
from sentinelai.auth.exceptions import (
    AccountInactiveError,
    AuthError,
    CSRFValidationError,
    InsufficientPermissionsError,
    InvalidTokenError,
    TokenExpiredError,
)
from sentinelai.auth.jwt_handler import decode_access_token
from sentinelai.auth.service import AuthService
from sentinelai.consent.service import ConsentService
from sentinelai.database.connection import get_db_session
from sentinelai.database.models.user import User
from sentinelai.database.repositories.user_repository import UserRepository
from sentinelai.users.service import UserService

# Optional HTTPBearer scheme (allows graceful handling and custom exception formats)
_bearer_scheme = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------------------
# Service Injection Dependencies
# ------------------------------------------------------------------------------
async def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    """Dependency injecting AuthService with request-scoped database session."""
    return AuthService(session)


async def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    """Dependency injecting UserService with request-scoped database session."""
    return UserService(session)


async def get_consent_service(session: AsyncSession = Depends(get_db_session)) -> ConsentService:
    """Dependency injecting ConsentService with request-scoped database session."""
    return ConsentService(session)


# ------------------------------------------------------------------------------
# User Authentication Dependencies
# ------------------------------------------------------------------------------
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Extract, decode, and verify JWT bearer access token, resolving the database User.

    Returns:
        Active, authenticated User instance with loaded roles.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.
        HTTPException: 403 if user account is deactivated.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required in 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except TokenExpiredError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except (InvalidTokenError, Exception) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token subject identifier missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(user_id_raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user subject in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or suspended.",
        )

    return user


async def require_authenticated_user(
    user: User = Depends(get_current_user),
) -> User:
    """Explicit dependency ensuring caller is authenticated and active."""
    return user


# ------------------------------------------------------------------------------
# Role-Based Access Control (RBAC) Guard Factory
# ------------------------------------------------------------------------------
def require_role(*allowed_roles: str) -> Callable:
    """Create a dependency guard that verifies the user possesses at least one allowed role.

    Super-admin ('SUPER_ADMIN') always satisfies all permissions.
    Equivalence between 'USER' and 'END_USER' is supported.

    Args:
        *allowed_roles: Roles permitted to access the endpoint (e.g. 'ADMIN', 'USER').

    Returns:
        FastAPI async dependency callable returning the authorized User.
    """
    normalized_allowed = {r.strip().upper() for r in allowed_roles}
    if "USER" in normalized_allowed:
        normalized_allowed.add("END_USER")
    if "END_USER" in normalized_allowed:
        normalized_allowed.add("USER")

    async def _role_guard(user: User = Depends(get_current_user)) -> User:
        user_roles = {r.name.strip().upper() for r in user.roles}

        # SUPER_ADMIN bypasses all role constraints
        if "SUPER_ADMIN" in user_roles:
            return user

        # Check intersection
        if not user_roles.intersection(normalized_allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: this resource requires one of the following roles: {sorted(list(normalized_allowed))}",
            )

        return user

    return _role_guard


# Shorthand RBAC dependencies
require_admin = require_role("ADMIN", "SUPER_ADMIN")
require_user = require_role("USER", "END_USER", "ADMIN", "SUPER_ADMIN")


# ------------------------------------------------------------------------------
# CSRF Guard Dependency
# ------------------------------------------------------------------------------
async def verify_csrf_token(request: Request) -> None:
    """Validate Double-Submit CSRF token for cookie-based state-changing requests.

    Requests authenticated with Bearer tokens in Authorization headers are exempt,
    as they are inherently protected against ambient credential injection.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.strip().startswith("Bearer "):
        # Bearer token present: exempt from CSRF
        return

    header_token = request.headers.get(CSRF_HEADER_NAME)
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)

    try:
        validate_double_submit_csrf(header_token, cookie_token)
    except CSRFValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=err.message,
        ) from err

