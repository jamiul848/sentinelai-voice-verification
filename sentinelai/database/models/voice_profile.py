"""Sentinel Voice - Voice Profile Model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentinelai.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sentinelai.database.models.enrollment_record import EnrollmentRecord
    from sentinelai.database.models.user import User
    from sentinelai.database.models.verification_event import VerificationEvent


class VoiceProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Voice profile lifecycle entity pointing to isolated encrypted vector container.

    INVARIANT: Never stores raw embedding vectors in database columns.
    """

    __tablename__ = "voice_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        nullable=False,
        index=True,
    )  # ACTIVE, REVOKED
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mean_pairwise_similarity: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    model_identifier: Mapped[str] = mapped_column(
        String(100),
        default="speechbrain/spkrec-ecapa-voxceleb",
        nullable=False,
    )
    embedding_storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    embedding_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="voice_profiles")
    enrollment_records: Mapped[List["EnrollmentRecord"]] = relationship(
        "EnrollmentRecord",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="EnrollmentRecord.created_at",
        lazy="selectin",
    )
    verification_events: Mapped[List["VerificationEvent"]] = relationship(
        "VerificationEvent",
        back_populates="profile",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("sample_count >= 3", name="check_min_enrollment_samples"),
        Index("idx_voice_profiles_user_status", "user_id", "status"),
    )

