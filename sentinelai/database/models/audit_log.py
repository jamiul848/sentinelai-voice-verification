"""Sentinel Voice - Administrative Audit Log Model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sentinelai.database.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from sentinelai.database.models.user import User


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """Immutable ledger of administrative and security events.

    INVARIANT: Sensitive cryptographic keys and vector payloads are strictly omitted from `changes`.
    """

    __tablename__ = "audit_logs"

    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False)
    changes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    actor_user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_actor_time", "actor_user_id", "created_at"),
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
    )

