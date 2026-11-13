"""Sentinel Voice - Enrollment Record Acoustic Metadata Model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import (
    CheckConstraint,
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
    from sentinelai.database.models.voice_profile import VoiceProfile


class EnrollmentRecord(Base, UUIDPrimaryKeyMixin):
    """Acoustic metadata for an individual utterance used in centroid creation.

    INVARIANT: Stored purely as numerical metadata; zero audio waveforms or bytes.
    """

    __tablename__ = "enrollment_records"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("voice_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duration_sec: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False)
    rms_energy: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    peak_amplitude: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    snr_db: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)
    audio_format: Mapped[str] = mapped_column(String(10), nullable=False)  # WAV or FLAC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )

    profile: Mapped["VoiceProfile"] = relationship(
        "VoiceProfile",
        back_populates="enrollment_records",
    )

    __table_args__ = (
        CheckConstraint("duration_sec >= 1.0 AND duration_sec <= 60.0", name="check_enrollment_duration_range"),
        Index("idx_enrollment_records_profile_created", "profile_id", "created_at"),
    )

