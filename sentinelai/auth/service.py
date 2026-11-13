"""Sentinel Voice - Authentication Service.

Orchestrates user registration, authentication, JWT issuance, refresh token rotation,
and session revocation with comprehensive audit logging.
"""

from datetime import datetime, timezone
from datetime import timedelta
import logging
from typing import Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.auth.csrf import generate_csrf_token
from sentinelai.auth.exceptions import (
    AccountInactiveError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    TokenReusedError,
)
from sentinelai.auth.jwt_handler import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from sentinelai.auth.password import hash_password, verify_password
from sentinelai.auth.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRegistrationRequest,
    UserResponse,
)
from sentinelai.config import get_settings
from sentinelai.database.base import utc_now
from sentinelai.database.models.user import User
from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and session lifecycle service."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditRepository(session)
        self.settings = get_settings()

    async def register_user(
        self,
        req: UserRegistrationRequest,
        ip_address: Optional[str] = None,
    ) -> User:
        """Register a new user account with default USER role.

        INVARIANT: New registrants are never granted administrator privileges.

        Args:
            req: Registration input payload.
            ip_address: Client IP address for audit records.

        Returns:
            Created User instance with preloaded roles.

        Raises:
            EmailAlreadyExistsError: If email is already in use.
        """
        normalized_email = req.email.strip().lower()
        existing = await self.user_repo.get_by_email(normalized_email)
        if existing is not None:
            raise EmailAlreadyExistsError("Email address is already registered.")

        # Hash password with Argon2id
        hashed_pw = hash_password(req.password)

        # Create user record
        user = await self.user_repo.create_user(
            email=normalized_email,
            hashed_password=hashed_pw,
            full_name=req.full_name.strip(),
            is_active=True,
            is_verified=False,
        )

        # Ensure default 'USER' role exists and assign it
        role = await self.user_repo.get_role_by_name("USER")
        if role is None:
            # Fallback check for END_USER or create USER
            role = await self.user_repo.get_role_by_name("END_USER")
            if role is None:
                role = await self.user_repo.create_role(
                    name="USER",
                    description="Standard application end-user",
                    permissions=["verify", "view_own_profile"],
                )

        await self.user_repo.assign_role(user.id, role.id)

        # Audit log registration
        await self.audit_repo.create_audit_event(
            action="USER_REGISTERED",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            changes={
                "email": normalized_email,
                "full_name": user.full_name,
                "role_assigned": role.name,
                "ip_address": ip_address,
            },
        )

        await self.session.commit()
        # Re-fetch user with relations loaded
        refreshed_user = await self.user_repo.get_by_id(user.id)
        return refreshed_user or user

    async def authenticate_user(
        self,
        req: UserLoginRequest,
        ip_address: Optional[str] = None,
    ) -> Tuple[TokenResponse, User]:
        """Authenticate user credentials and issue token pair.

        INVARIANT: Never reveals whether an email exists on failure.

        Args:
            req: Login credential payload.
            ip_address: Client IP address.

        Returns:
            Tuple of (TokenResponse, User).

        Raises:
            InvalidCredentialsError: If email or password is incorrect.
            AccountInactiveError: If the account is deactivated.
        """
        user = await self.user_repo.get_by_email(req.email)
        if user is None:
            # Constant-time mitigation: perform dummy verify to prevent timing side-channels
            verify_password("dummy_password", "$argon2id$v=19$m=65536,t=3,p=2$dGVzdHNhbHQ$dGVzdGhhc2g")
            raise InvalidCredentialsError("Invalid email or password.")

        if not verify_password(req.password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            raise AccountInactiveError("Account is inactive or suspended. Please contact an administrator.")

        # Resolve role names
        role_names = [r.name for r in user.roles] or ["USER"]

        # Issue access token
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=role_names,
        )

        # Generate and hash refresh token
        raw_refresh, refresh_hash = generate_refresh_token()
        expires_at = utc_now() + timedelta(days=self.settings.refresh_token_expire_days)

        await self.user_repo.create_refresh_token(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        )

        csrf_token = generate_csrf_token()

        # Audit log login
        await self.audit_repo.create_audit_event(
            action="USER_LOGIN",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            changes={"ip_address": ip_address},
        )

        await self.session.commit()

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
            csrf_token=csrf_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                roles=role_names,
                created_at=user.created_at,
            ),
        )

        return token_response, user

    async def rotate_refresh_token(
        self,
        raw_refresh_token: str,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Rotate a refresh token, issuing a new token pair and revoking the old token.

        Detects token reuse and invalidates the entire session family for the user.

        Args:
            raw_refresh_token: Client-provided raw refresh token.
            ip_address: Client IP address.

        Returns:
            Fresh TokenResponse.

        Raises:
            InvalidTokenError: If token is malformed or not found.
            TokenReusedError: If token was previously revoked (breach detection).
            TokenExpiredError: If token has expired.
            AccountInactiveError: If user is inactive.
        """
        token_hash = hash_refresh_token(raw_refresh_token)
        token_record = await self.user_repo.get_refresh_token(token_hash)

        if token_record is None:
            raise InvalidTokenError("Invalid refresh token.")

        # Breach detection: reuse of already revoked token
        if token_record.is_revoked:
            logger.warning(
                "Refresh token reuse detected for user %s! Revoking all sessions.",
                token_record.user_id,
            )
            # Invalidate all active sessions for this user
            await self.user_repo.revoke_all_user_tokens(token_record.user_id)
            await self.audit_repo.create_audit_event(
                action="TOKEN_REUSE_DETECTED",
                resource_type="refresh_token",
                resource_id=str(token_record.id),
                actor_user_id=token_record.user_id,
                changes={"ip_address": ip_address, "action": "family_revocation"},
            )
            await self.session.commit()
            raise TokenReusedError(
                "Refresh token reuse detected. All active sessions have been revoked for security."
            )

        # Check expiration
        record_exp = (
            token_record.expires_at
            if token_record.expires_at.tzinfo is not None
            else token_record.expires_at.replace(tzinfo=timezone.utc)
        )
        if record_exp < utc_now():
            await self.user_repo.revoke_refresh_token(token_hash)
            await self.session.commit()
            raise TokenExpiredError("Refresh token has expired.")

        # Check user status
        user = await self.user_repo.get_by_id(token_record.user_id)
        if user is None or not user.is_active:
            raise AccountInactiveError("User account is inactive or not found.")

        # Revoke the consumed token
        await self.user_repo.revoke_refresh_token(token_hash)

        # Generate new refresh token pair
        new_raw_refresh, new_refresh_hash = generate_refresh_token()
        new_expires_at = utc_now() + timedelta(days=self.settings.refresh_token_expire_days)

        await self.user_repo.create_refresh_token(
            user_id=user.id,
            token_hash=new_refresh_hash,
            expires_at=new_expires_at,
        )

        role_names = [r.name for r in user.roles] or ["USER"]
        new_access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            roles=role_names,
        )

        csrf_token = generate_csrf_token()

        await self.audit_repo.create_audit_event(
            action="TOKEN_ROTATED",
            resource_type="refresh_token",
            resource_id=str(token_record.id),
            actor_user_id=user.id,
            changes={"ip_address": ip_address},
        )

        await self.session.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
            csrf_token=csrf_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                is_verified=user.is_verified,
                roles=role_names,
                created_at=user.created_at,
            ),
        )

    async def logout_user(
        self,
        user: Optional[User] = None,
        raw_refresh_token: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Revoke refresh token session and log out.

        Idempotent: safe on repeated invocations.

        Args:
            user: Authenticated User (if available).
            raw_refresh_token: Specific refresh token to invalidate.
            ip_address: Client IP address.

        Returns:
            True if logout succeeded.
        """
        revoked_count = 0

        if raw_refresh_token:
            token_hash = hash_refresh_token(raw_refresh_token)
            success = await self.user_repo.revoke_refresh_token(token_hash)
            if success:
                revoked_count += 1

        if user is not None and not raw_refresh_token:
            revoked_count = await self.user_repo.revoke_all_user_tokens(user.id)

        user_id = user.id if user else None
        await self.audit_repo.create_audit_event(
            action="USER_LOGOUT",
            resource_type="user",
            resource_id=str(user_id) if user_id else "unknown",
            actor_user_id=user_id,
            changes={"revoked_count": revoked_count, "ip_address": ip_address},
        )

        await self.session.commit()
        return True
