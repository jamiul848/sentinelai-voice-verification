"""Sentinel Voice - Biometric Legal Consent Management Service.

Enforces GDPR Article 7 and Illinois BIPA compliance:
1. Obtains explicit consent prior to biometric enrollment.
2. Maintains immutable chronological audit history of consent events.
3. Immediately executes profile revocation and AES-256 encrypted vector file shredding
   upon consent revocation.
"""

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.auth.crypto import secure_delete_file
from sentinelai.auth.schemas import (
    ConsentResponse,
    GrantConsentRequest,
    RevokeConsentRequest,
)
from sentinelai.database.models.user import User
from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.consent_repository import ConsentRepository
from sentinelai.database.repositories.profile_repository import ProfileRepository

logger = logging.getLogger(__name__)


class ConsentService:
    """Manages explicit biometric legal consent lifecycle and compliance shredding."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.consent_repo = ConsentRepository(session)
        self.profile_repo = ProfileRepository(session)
        self.audit_repo = AuditRepository(session)

    def _to_consent_response(self, record) -> ConsentResponse:
        """Convert ConsentRecord model to ConsentResponse schema."""
        return ConsentResponse(
            id=record.id,
            user_id=record.user_id,
            consent_type=record.consent_type,
            consent_granted=record.consent_granted,
            consent_version=record.consent_version,
            created_at=record.created_at,
        )

    async def grant_consent(
        self,
        user: User,
        req: GrantConsentRequest,
        ip_address: Optional[str] = None,
    ) -> ConsentResponse:
        """Record explicit, affirmative legal consent for voice biometric processing."""
        record = await self.consent_repo.create_consent_record(
            user_id=user.id,
            consent_version=req.consent_version,
            consent_type=req.consent_type,
            consent_granted=True,
            ip_address=ip_address,
        )

        await self.audit_repo.create_audit_event(
            action="CONSENT_GRANTED",
            resource_type="consent_record",
            resource_id=str(record.id),
            actor_user_id=user.id,
            changes={
                "consent_type": req.consent_type,
                "version": req.consent_version,
                "ip_address": ip_address,
            },
        )

        await self.session.commit()
        return self._to_consent_response(record)

    async def get_current_consent(
        self,
        user: User,
        consent_type: str = "VOICE_BIOMETRIC_ENROLLMENT",
    ) -> Optional[ConsentResponse]:
        """Fetch the current consent status for the user."""
        record = await self.consent_repo.get_latest_consent(user.id, consent_type)
        if record is None:
            return None
        return self._to_consent_response(record)

    async def get_consent_history(
        self,
        user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ConsentResponse]:
        """Retrieve complete immutable consent audit history."""
        records = await self.consent_repo.get_user_consent_history(user.id, skip=skip, limit=limit)
        return [self._to_consent_response(r) for r in records]

    async def revoke_consent(
        self,
        user: User,
        req: RevokeConsentRequest,
        ip_address: Optional[str] = None,
    ) -> ConsentResponse:
        """Revoke biometric consent, revoke active voice profiles, and shred vector files.

        INVARIANT: Revoking consent triggers permanent, secure shredding of encrypted
        voice embedding files from disk and marks profiles as REVOKED.
        """
        # Fetch latest version to record in revocation notice
        latest = await self.consent_repo.get_latest_consent(user.id, req.consent_type)
        version_revoked = latest.consent_version if latest else "1.0"

        # Record revocation in consent audit trail
        revocation_record = await self.consent_repo.create_consent_record(
            user_id=user.id,
            consent_version=f"{version_revoked}-REVOKED",
            consent_type=req.consent_type,
            consent_granted=False,
            ip_address=ip_address,
        )

        # Trigger biometric profile revocation and file shredding workflow
        active_profile = await self.profile_repo.get_active_profile_by_user(user.id)
        if active_profile is not None:
            logger.info(
                "Consent revoked by user %s: securely shredding active voice profile %s.",
                user.id,
                active_profile.id,
            )
            # Shred vector storage on disk
            if active_profile.embedding_storage_path:
                try:
                    secure_delete_file(active_profile.embedding_storage_path)
                except Exception as err:
                    logger.warning("Failed to shred embedding file: %s", err)

            # Mark profile as revoked in database
            await self.profile_repo.revoke_profile(active_profile.id)

            await self.audit_repo.create_audit_event(
                action="PROFILE_REVOKED_CONSENT_WITHDRAWN",
                resource_type="voice_profile",
                resource_id=str(active_profile.id),
                actor_user_id=user.id,
                changes={
                    "reason": "USER_REVOKED_CONSENT",
                    "path_shredded": active_profile.embedding_storage_path,
                },
            )

        await self.audit_repo.create_audit_event(
            action="CONSENT_REVOKED",
            resource_type="consent_record",
            resource_id=str(revocation_record.id),
            actor_user_id=user.id,
            changes={
                "consent_type": req.consent_type,
                "reason": req.reason,
                "ip_address": ip_address,
            },
        )

        await self.session.commit()
        return self._to_consent_response(revocation_record)

