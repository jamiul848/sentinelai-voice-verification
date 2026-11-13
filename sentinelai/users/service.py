"""Sentinel Voice - User Management Service.

Handles self-service profile updates, password modification, session termination,
and administrative user lifecycle management with strict anti-escalation safeguards.
"""

import logging
from typing import List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.auth.exceptions import (
    InvalidCredentialsError,
    LastAdminError,
    SelfModificationError,
    UserNotFoundError,
)
from sentinelai.auth.password import hash_password, verify_password
from sentinelai.auth.schemas import (
    AdminUpdateRolesRequest,
    AdminUpdateStatusRequest,
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserResponse,
)
from sentinelai.database.models.user import User
from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Service handling profile operations, password resets, and admin controls."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditRepository(session)

    def _to_user_response(self, user: User) -> UserResponse:
        """Convert User ORM model to sanitized UserResponse."""
        role_names = [r.name for r in user.roles] or ["USER"]
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=role_names,
            created_at=user.created_at,
        )

    # --------------------------------------------------------------------------
    # User Self-Service Endpoints
    # --------------------------------------------------------------------------
    async def get_current_user_profile(self, user: User) -> UserResponse:
        """Return the sanitized profile for the authenticated user."""
        refreshed = await self.user_repo.get_by_id(user.id)
        return self._to_user_response(refreshed or user)

    async def update_profile(
        self,
        user: User,
        req: UpdateProfileRequest,
        ip_address: Optional[str] = None,
    ) -> UserResponse:
        """Update permitted self-service profile fields.

        INVARIANT: End-users cannot modify their own roles or active status.
        """
        changes = {}
        if req.full_name is not None and req.full_name.strip():
            user.full_name = req.full_name.strip()
            changes["full_name"] = user.full_name

        if changes:
            await self.audit_repo.create_audit_event(
                action="USER_PROFILE_UPDATED",
                resource_type="user",
                resource_id=str(user.id),
                actor_user_id=user.id,
                changes={**changes, "ip_address": ip_address},
            )
            await self.session.commit()

        refreshed = await self.user_repo.get_by_id(user.id)
        return self._to_user_response(refreshed or user)

    async def change_password(
        self,
        user: User,
        req: ChangePasswordRequest,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Change account password and revoke all existing refresh token sessions.

        Args:
            user: Authenticated User model.
            req: Password change payload.
            ip_address: Client IP address.

        Returns:
            True on success.

        Raises:
            InvalidCredentialsError: If current password verification fails.
        """
        # Re-fetch user to get latest hashed_password
        db_user = await self.user_repo.get_by_id(user.id)
        if db_user is None or not verify_password(req.current_password, db_user.hashed_password):
            raise InvalidCredentialsError("Current password is incorrect.")

        new_hash = hash_password(req.new_password)
        db_user.hashed_password = new_hash

        # Revoke all existing refresh tokens
        revoked_sessions = await self.user_repo.revoke_all_user_tokens(db_user.id)

        await self.audit_repo.create_audit_event(
            action="PASSWORD_CHANGED",
            resource_type="user",
            resource_id=str(db_user.id),
            actor_user_id=db_user.id,
            changes={"revoked_sessions": revoked_sessions, "ip_address": ip_address},
        )

        await self.session.commit()
        return True

    # --------------------------------------------------------------------------
    # Administrative User Controls (ADMIN-Only)
    # --------------------------------------------------------------------------
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = False,
    ) -> List[UserResponse]:
        """Fetch paginated list of all registered users."""
        users = await self.user_repo.list_users(skip=skip, limit=limit, active_only=active_only)
        return [self._to_user_response(u) for u in users]

    async def get_user_by_id(self, user_id: uuid.UUID) -> UserResponse:
        """Fetch user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"User with ID '{user_id}' does not exist.")
        return self._to_user_response(user)

    async def update_user_status(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        req: AdminUpdateStatusRequest,
        ip_address: Optional[str] = None,
    ) -> UserResponse:
        """Enable or disable a user account.

        Guards:
        - Prevents administrators from deactivating themselves.
        - Prevents deactivating the last active administrator.
        """
        target = await self.user_repo.get_by_id(target_user_id)
        if target is None:
            raise UserNotFoundError(f"User with ID '{target_user_id}' does not exist.")

        # Guard: self-deactivation forbidden
        if admin_user.id == target_user_id and not req.is_active:
            raise SelfModificationError("Administrators cannot deactivate their own account.")

        # Guard: last active admin deactivation forbidden
        if not req.is_active:
            is_target_admin = any(r.name in ["ADMIN", "SUPER_ADMIN"] for r in target.roles)
            if is_target_admin:
                active_admins = await self.user_repo.count_active_admins()
                if active_admins <= 1:
                    raise LastAdminError(
                        "Cannot deactivate the last active administrator in the system."
                    )

        target.is_active = req.is_active

        # If deactivating, revoke all active sessions
        if not req.is_active:
            await self.user_repo.revoke_all_user_tokens(target.id)

        await self.audit_repo.create_audit_event(
            action="ADMIN_USER_STATUS_UPDATED",
            resource_type="user",
            resource_id=str(target.id),
            actor_user_id=admin_user.id,
            changes={"is_active": req.is_active, "ip_address": ip_address},
        )

        await self.session.commit()
        refreshed = await self.user_repo.get_by_id(target.id)
        return self._to_user_response(refreshed or target)

    async def update_user_roles(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        req: AdminUpdateRolesRequest,
        ip_address: Optional[str] = None,
    ) -> UserResponse:
        """Assign explicit RBAC roles to a user account.

        Guards:
        - Prevents the last administrator from stripping their own administrator role.
        """
        target = await self.user_repo.get_by_id(target_user_id)
        if target is None:
            raise UserNotFoundError(f"User with ID '{target_user_id}' does not exist.")

        requested_roles = [r.upper() for r in req.roles]
        admin_role_requested = any(r in ["ADMIN", "SUPER_ADMIN"] for r in requested_roles)

        # Guard: last admin demoting themselves
        if admin_user.id == target_user_id and not admin_role_requested:
            active_admins = await self.user_repo.count_active_admins()
            if active_admins <= 1:
                raise LastAdminError(
                    "Cannot remove administrator privileges from the last active administrator."
                )

        # Clear existing role assignments and apply new roles
        current_roles = list(target.roles)
        for r in current_roles:
            await self.user_repo.remove_role(target.id, r.id)

        for role_name in requested_roles:
            role = await self.user_repo.get_role_by_name(role_name)
            if role is None:
                role = await self.user_repo.create_role(
                    name=role_name,
                    description=f"Role {role_name}",
                    permissions=["verify"],
                )
            await self.user_repo.assign_role(target.id, role.id)

        await self.audit_repo.create_audit_event(
            action="ADMIN_USER_ROLES_UPDATED",
            resource_type="user",
            resource_id=str(target.id),
            actor_user_id=admin_user.id,
            changes={"new_roles": requested_roles, "ip_address": ip_address},
        )

        await self.session.commit()
        refreshed = await self.user_repo.get_by_id(target.id)
        return self._to_user_response(refreshed or target)

    async def delete_user(
        self,
        admin_user: User,
        target_user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Delete a user account.

        Guards:
        - Prevents administrators from deleting themselves.
        - Prevents deleting the last active administrator.
        """
        target = await self.user_repo.get_by_id(target_user_id)
        if target is None:
            raise UserNotFoundError(f"User with ID '{target_user_id}' does not exist.")

        if admin_user.id == target_user_id:
            raise SelfModificationError("Administrators cannot delete their own account.")

        is_target_admin = any(r.name in ["ADMIN", "SUPER_ADMIN"] for r in target.roles)
        if is_target_admin:
            active_admins = await self.user_repo.count_active_admins()
            if active_admins <= 1:
                raise LastAdminError(
                    "Cannot delete the last active administrator in the system."
                )

        # Revoke all tokens first
        await self.user_repo.revoke_all_user_tokens(target_user_id)

        # Delete user
        await self.user_repo.delete_user(target_user_id)

        await self.audit_repo.create_audit_event(
            action="ADMIN_USER_DELETED",
            resource_type="user",
            resource_id=str(target_user_id),
            actor_user_id=admin_user.id,
            changes={"deleted_email": target.email, "ip_address": ip_address},
        )

        await self.session.commit()
        return True

