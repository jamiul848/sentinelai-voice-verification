"""Sentinel Voice - Verification Event Repository."""

from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.database.models.verification_event import VerificationEvent
from sentinelai.database.repositories.base import BaseRepository


class VerificationRepository(BaseRepository[VerificationEvent]):
    """Repository handling append-only VerificationEvent logging and history queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VerificationEvent, session)

    async def create_verification_event(
        self,
        user_id: uuid.UUID,
        decision: str,
        similarity_score: float,
        applied_threshold: float,
        is_match: bool,
        processing_time_ms: float,
        profile_id: Optional[uuid.UUID] = None,
        client_ip: Optional[str] = None,
    ) -> VerificationEvent:
        """Create and persist a new verification decision transaction."""
        event = VerificationEvent(
            user_id=user_id,
            profile_id=profile_id,
            decision=decision.upper(),
            similarity_score=similarity_score,
            applied_threshold=applied_threshold,
            is_match=is_match,
            processing_time_ms=processing_time_ms,
            client_ip=client_ip,
        )
        return await self.add(event)

    async def get_verification_by_id(
        self,
        event_id: uuid.UUID,
    ) -> Optional[VerificationEvent]:
        """Fetch verification event record by UUID primary key."""
        return await self.get_by_id(event_id)

    async def get_user_verification_history(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[VerificationEvent]:
        """Fetch verification attempts for a specific user ordered by created_at descending."""
        stmt = (
            select(VerificationEvent)
            .where(VerificationEvent.user_id == user_id)
            .order_by(desc(VerificationEvent.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

