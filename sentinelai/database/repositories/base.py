"""Sentinel Voice - Generic Async Base Repository."""

from typing import Any, Generic, List, Optional, Type, TypeVar
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing foundational database access methods."""

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        """Initialize repository with model class and active session.

        Args:
            model: SQLAlchemy model class.
            session: Active AsyncSession.
        """
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: Any) -> Optional[ModelType]:
        """Fetch a single record by primary key."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalars().first()

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ModelType]:
        """Fetch a paginated list of records."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total records for this entity."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def add(self, entity: ModelType) -> ModelType:
        """Add and flush entity to active session."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

