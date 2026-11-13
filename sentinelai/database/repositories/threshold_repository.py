"""Sentinel Voice - Dynamic Threshold Configuration Repository."""

from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.database.base import utc_now
from sentinelai.database.models.threshold_configuration import ThresholdConfiguration
from sentinelai.database.repositories.base import BaseRepository


class ThresholdRepository(BaseRepository[ThresholdConfiguration]):
    """Repository handling dynamic threshold configurations, calibration provenance, and model matching."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ThresholdConfiguration, session)

    async def get_active_threshold(
        self,
        model_identifier: str = "speechbrain/spkrec-ecapa-voxceleb",
    ) -> Optional[ThresholdConfiguration]:
        """Fetch the currently active decision threshold for a specified neural model.

        Args:
            model_identifier: Identifier of the speaker recognition backbone model.

        Returns:
            Active ThresholdConfiguration instance, or None if none is active.
        """
        stmt = (
            select(ThresholdConfiguration)
            .where(
                ThresholdConfiguration.model_identifier == model_identifier,
                ThresholdConfiguration.is_active.is_(True),
            )
            .order_by(desc(ThresholdConfiguration.updated_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_version(
        self,
        version_tag: str,
    ) -> Optional[ThresholdConfiguration]:
        """Fetch a specific threshold configuration by version tag."""
        stmt = select(ThresholdConfiguration).where(
            ThresholdConfiguration.version_tag == version_tag
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_threshold(
        self,
        version_tag: str,
        model_identifier: str,
        threshold_value: float,
        calibration_dataset: str,
        calibration_criterion: str = "equal_error_rate_minimization",
        calibration_metadata: Optional[Dict[str, Any]] = None,
        is_active: bool = False,
    ) -> ThresholdConfiguration:
        """Create and persist a new calibrated threshold configuration."""
        if is_active:
            # Deactivate existing active configurations for this model
            stmt = (
                update(ThresholdConfiguration)
                .where(
                    ThresholdConfiguration.model_identifier == model_identifier,
                    ThresholdConfiguration.is_active.is_(True),
                )
                .values(is_active=False, updated_at=utc_now())
            )
            await self.session.execute(stmt)

        config = ThresholdConfiguration(
            version_tag=version_tag,
            model_identifier=model_identifier,
            threshold_value=threshold_value,
            calibration_dataset=calibration_dataset,
            calibration_criterion=calibration_criterion,
            calibration_metadata=calibration_metadata or {},
            is_active=is_active,
        )
        return await self.add(config)

    async def list_configurations(
        self,
        model_identifier: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ThresholdConfiguration]:
        """Fetch all threshold configurations, optionally filtered by model."""
        stmt = select(ThresholdConfiguration)
        if model_identifier:
            stmt = stmt.where(ThresholdConfiguration.model_identifier == model_identifier)
        stmt = stmt.order_by(desc(ThresholdConfiguration.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def activate_threshold(
        self,
        configuration_id: uuid.UUID,
    ) -> Optional[ThresholdConfiguration]:
        """Set a configuration as the active threshold for its model, deactivating others."""
        target = await self.get_by_id(configuration_id)
        if not target:
            return None

        # Deactivate all others for this model
        stmt = (
            update(ThresholdConfiguration)
            .where(
                ThresholdConfiguration.model_identifier == target.model_identifier,
                ThresholdConfiguration.id != target.id,
                ThresholdConfiguration.is_active.is_(True),
            )
            .values(is_active=False, updated_at=utc_now())
        )
        await self.session.execute(stmt)

        target.is_active = True
        target.updated_at = utc_now()
        await self.session.flush()
        await self.session.refresh(target)
        return target

