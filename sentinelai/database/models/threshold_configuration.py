"""Sentinel Voice - Dynamic Threshold Configuration Model.

Manages active and historical decision thresholds dynamically with calibration provenance,
avoiding hardcoded values across application logic.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from sentinelai.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class ThresholdConfiguration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Dynamic decision threshold configuration and provenance ledger."""

    __tablename__ = "threshold_configurations"

    version_tag: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    model_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    threshold_value: Mapped[float] = mapped_column(
        Numeric(7, 6),
        nullable=False,
    )
    calibration_dataset: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    calibration_criterion: Mapped[str] = mapped_column(
        String(50),
        default="equal_error_rate_minimization",
        nullable=False,
    )
    calibration_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("idx_threshold_config_active_model", "model_identifier", "is_active"),
    )

