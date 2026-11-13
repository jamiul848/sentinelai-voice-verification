"""Sentinel Voice - Verification Event Model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentinelai.database.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sentinelai.database.models.threshold_configuration import ThresholdConfiguration
    from sentinelai.database.models.user import User
    from sentinelai.database.models.voice_profile import VoiceProfile


class VerificationEvent(Base, UUIDPrimaryKeyMixin):
    """Immutable audit entry for an individual speaker verification transaction."""

    __tablename__ = "verification_events"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("voice_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    threshold_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("threshold_configurations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # MATCH or NO_MATCH
    similarity_score: Mapped[float] = mapped_column(Numeric(7, 6), nullable=False)
    applied_threshold: Mapped[float] = mapped_column(Numeric(7, 6), nullable=False)
    is_match: Mapped[bool] = mapped_column(Boolean, nullable=False)
    processing_time_ms: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="verification_events")
    profile: Mapped[Optional["VoiceProfile"]] = relationship("VoiceProfile", back_populates="verification_events")
    threshold: Mapped[Optional["ThresholdConfiguration"]] = relationship("ThresholdConfiguration")

    __table_args__ = (
        Index("idx_verif_events_user_time", "user_id", "created_at"),
        Index("idx_verif_events_decision_time", "decision", "created_at"),
    )

