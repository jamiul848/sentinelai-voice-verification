"""Sentinel Voice - Administrative Audit Log Repository."""

from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.database.models.audit_log import AuditLog
from sentinelai.database.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Repository handling append-only immutable audit logging."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AuditLog, session)

    async def create_audit_event(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        actor_user_id: Optional[uuid.UUID] = None,
        changes: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create and persist an append-only audit event record.

        Args:
            action: Action string (e.g. 'USER_REGISTERED', 'PROFILE_REVOKED').
            resource_type: Type of modified resource (e.g. 'user', 'voice_profile').
            resource_id: Identifier of modified entity.
            actor_user_id: Performing user ID or None for system actions.
            changes: Safe JSON snapshot of delta changes (omitting passwords/vectors).

        Returns:
            Created AuditLog instance.
        """
        event = AuditLog(
            action=action.upper(),
            resource_type=resource_type.lower(),
            resource_id=str(resource_id),
            actor_user_id=actor_user_id,
            changes=changes,
        )
        return await self.add(event)

    async def get_audit_history(
        self,
        actor_user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AuditLog]:
        """Fetch audit log entries optionally filtered by actor, ordered by created_at descending."""
        stmt = select(AuditLog)
        if actor_user_id:
            stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
        stmt = stmt.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_resource_events(
        self,
        resource_type: str,
        resource_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AuditLog]:
        """Fetch all audit events associated with a specific resource entity."""
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.resource_type == resource_type.lower(),
                AuditLog.resource_id == str(resource_id),
            )
            .order_by(desc(AuditLog.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

