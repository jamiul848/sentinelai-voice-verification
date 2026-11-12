"""Sentinel Voice - Biometric Legal Consent Repository."""

from typing import List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.database.models.consent_record import ConsentRecord
from sentinelai.database.repositories.base import BaseRepository


class ConsentRepository(BaseRepository[ConsentRecord]):
    """Repository handling biometric consent registration and legal compliance verification."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ConsentRecord, session)

    async def create_consent_record(
        self,
        user_id: uuid.UUID,
        consent_version: str,
        consent_type: str = "VOICE_BIOMETRIC_ENROLLMENT",
        ip_address: Optional[str] = None,
    ) -> ConsentRecord:
        """Create and persist an explicit legal biometric consent transaction."""
        consent = ConsentRecord(
            user_id=user_id,
            consent_type=consent_type,
            consent_granted=True,
            consent_version=consent_version,
            ip_address=ip_address,
        )
        return await self.add(consent)

    async def get_user_consent_history(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ConsentRecord]:
        """Fetch immutable chronological consent history for a user."""
        stmt = (
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user_id)
            .order_by(desc(ConsentRecord.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_consent(
        self,
        user_id: uuid.UUID,
        consent_type: str = "VOICE_BIOMETRIC_ENROLLMENT",
    ) -> Optional[ConsentRecord]:
        """Fetch the latest active consent record for a user."""
        stmt = (
            select(ConsentRecord)
            .where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == consent_type,
                ConsentRecord.consent_granted.is_(True),
            )
            .order_by(desc(ConsentRecord.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

