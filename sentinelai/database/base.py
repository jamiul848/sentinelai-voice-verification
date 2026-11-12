"""Sentinel Voice - SQLAlchemy 2.0 Base & Common Mixins.

Provides:
- Base: DeclarativeBase for all relational entities.
- UUIDPrimaryKeyMixin: UUID primary key with uuid.uuid4 generator.
- TimestampMixin: created_at and updated_at with UTC timezone awareness.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return current timestamp in UTC timezone."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base class for all Sentinel Voice ORM models."""
    pass


class UUIDPrimaryKeyMixin:
    """Mixin adding an immutable UUID primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-10,
    )


class TimestampMixin:
    """Mixin adding created_at and updated_at UTC timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )

