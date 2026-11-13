"""Sentinel Voice - Biometric Legal Consent Record Model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentinelai.database.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sentinelai.database.models.user import User


class ConsentRecord(Base, UUIDPrimaryKeyMixin):
    """Immutable legal audit record of user biometric consent (GDPR / BIPA compliance).

    INVARIANT: Preserves historical consent records; never overwrites previous records.
    """

    __tablename__ = "consent_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type: Mapped[str] = mapped_column(
        String(50),
        default="VOICE_BIOMETRIC_ENROLLMENT",
        nullable=False,
    )
    consent_granted: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    consent_version: Mapped[str] = mapped_column(String(20), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="consent_records")

    __table_args__ = (
        Index("idx_consent_records_user_created", "user_id", "created_at"),
    )

