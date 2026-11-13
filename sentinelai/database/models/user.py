"""Sentinel Voice - User Account Model."""

from datetime import datetime
from typing import TYPE_CHECKING, List
import uuid

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from sentinelai.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from sentinelai.database.models.api_credential import ApiCredential
    from sentinelai.database.models.audit_log import AuditLog
    from sentinelai.database.models.consent_record import ConsentRecord
    from sentinelai.database.models.refresh_token import RefreshToken
    from sentinelai.database.models.role import Role
    from sentinelai.database.models.user_role import UserRole
    from sentinelai.database.models.verification_event import VerificationEvent
    from sentinelai.database.models.voice_profile import VoiceProfile


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Primary user account entity."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @validates("email")
    def validate_and_normalize_email(self, key: str, value: str) -> str:
        """Normalize email address to lowercase and stripped whitespace before persistence."""
        if not value or not isinstance(value, str):
            raise ValueError("Email must be a non-empty string.")
        normalized = value.strip().lower()
        if "@" not in normalized:
            raise ValueError(f"Invalid email format: '{value}'.")
        return normalized

    # RBAC relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
        overlaps="user_roles",
    )
    user_roles: Mapped[List["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        overlaps="roles,users",
    )

    # Session & API credential relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    api_credentials: Mapped[List["ApiCredential"]] = relationship(
        "ApiCredential",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Biometric & verification relationships
    consent_records: Mapped[List["ConsentRecord"]] = relationship(
        "ConsentRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    voice_profiles: Mapped[List["VoiceProfile"]] = relationship(
        "VoiceProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    verification_events: Mapped[List["VerificationEvent"]] = relationship(
        "VerificationEvent",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="actor_user",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_users_email_lower", func.lower(email)),
    )
