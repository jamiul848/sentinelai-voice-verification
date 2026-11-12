"""Sentinel Voice - User Repository."""

from datetime import datetime
from typing import Any, List, Optional
import uuid

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinelai.database.base import utc_now
from sentinelai.database.exceptions import DuplicateEntityError, EntityNotFoundError
from sentinelai.database.models.api_credential import ApiCredential
from sentinelai.database.models.refresh_token import RefreshToken
from sentinelai.database.models.role import Role
from sentinelai.database.models.user import User
from sentinelai.database.models.user_role import UserRole
from sentinelai.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling User accounts, RBAC roles, and authentication credentials."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def create_user(
        self,
        email: str,
        hashed_password: str,
        full_name: str,
        is_active: bool = True,
        is_verified: bool = False,
    ) -> User:
        """Create and persist a new user record.

        Args:
            email: User email address (normalized automatically by model).
            hashed_password: Argon2id or salted password hash string.
            full_name: User display name.
            is_active: Account active flag.
            is_verified: Email verification flag.

        Returns:
            Created User instance.

        Raises:
            DuplicateEntityError: If email is already registered.
        """
        normalized_email = email.strip().lower()
        existing = await self.get_by_email(normalized_email)
        if existing:
            raise DuplicateEntityError("User", "email", normalized_email)

        user = User(
            email=normalized_email,
            hashed_password=hashed_password,
            full_name=full_name.strip(),
            is_active=is_active,
            is_verified=is_verified,
        )
        return await self.add(user)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch user by UUID primary key."""
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email case-insensitively."""
        normalized = email.strip().lower()
        stmt = (
            select(User)
            .where(func.lower(User.email) == normalized)
            .options(selectinload(User.roles))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = False,
    ) -> List[User]:
        """Fetch a paginated list of users ordered by created_at descending."""
        stmt = select(User).options(selectinload(User.roles))
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))
        stmt = stmt.order_by(desc(User.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_user(
        self,
        user_id: uuid.UUID,
        **kwargs: Any,
    ) -> Optional[User]:
        """Update fields on an existing user record.

        Args:
            user_id: Target user UUID.
            **kwargs: Field key-value pairs to update.

        Returns:
            Updated User instance, or None if user not found.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = utc_now()
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def deactivate_user(self, user_id: uuid.UUID) -> Optional[User]:
        """Deactivate a user account (soft deactivation)."""
        return await self.update_user(user_id, is_active=False)

    # --------------------------------------------------------------------------
    # RBAC Role Assignment Helpers
    # --------------------------------------------------------------------------
    async def create_role(
        self,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[list] = None,
    ) -> Role:
        """Create a new RBAC role definition."""
        role = Role(
            name=name.upper(),
            description=description,
            permissions=permissions or [],
        )
        self.session.add(role)
        await self.session.flush()
        await self.session.refresh(role)
        return role

    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Fetch role by uppercase name."""
        stmt = select(Role).where(Role.name == name.upper())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def assign_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole:
        """Assign an RBAC role to a user.

        Raises:
            DuplicateEntityError: If role is already assigned to the user.
        """
        # Check duplicate assignment
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        existing = await self.session.execute(stmt)
        if existing.scalars().first() is not None:
            raise DuplicateEntityError("UserRole", "user_id_role_id", f"{user_id}:{role_id}")

        assignment = UserRole(user_id=user_id, role_id=role_id)
        self.session.add(assignment)
        await self.session.flush()
        await self.session.refresh(assignment)

        # Invalidate cached roles collection on the User model
        user = await self.session.get(User, user_id)
        if user is not None:
            self.session.expire(user, ["roles"])

        return assignment

    async def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Revoke a role assignment from a user."""
        stmt = delete(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        )
        res = await self.session.execute(stmt)
        await self.session.flush()
        user = await self.session.get(User, user_id)
        if user is not None:
            self.session.expire(user, ["roles"])
        return res.rowcount > 0

    # --------------------------------------------------------------------------
    # Refresh Token & API Credential Helpers
    # --------------------------------------------------------------------------
    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Create and persist a hashed refresh token session."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def revoke_refresh_token(self, token_hash: str) -> bool:
        """Mark a refresh token as revoked."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        res = await self.session.execute(stmt)
        token = res.scalars().first()
        if token and not token.is_revoked:
            token.is_revoked = True
            token.revoked_at = utc_now()
            await self.session.flush()
            return True
        return False

    async def create_api_credential(
        self,
        user_id: uuid.UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        scopes: Optional[list] = None,
    ) -> ApiCredential:
        """Create and persist developer API key credentials."""
        cred = ApiCredential(
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes or ["verify"],
            is_active=True,
        )
        self.session.add(cred)
        await self.session.flush()
        await self.session.refresh(cred)
        return cred

