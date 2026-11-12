"""Sentinel Voice - Voice Profile Repository."""

from typing import List, Optional
import uuid

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentinelai.database.base import utc_now
from sentinelai.database.exceptions import EntityNotFoundError
from sentinelai.database.models.enrollment_record import EnrollmentRecord
from sentinelai.database.models.voice_profile import VoiceProfile
from sentinelai.database.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[VoiceProfile]):
    """Repository handling VoiceProfile lifecycles and enrollment records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(VoiceProfile, session)

    async def create_profile(
        self,
        user_id: uuid.UUID,
        sample_count: int,
        mean_pairwise_similarity: float,
        embedding_storage_path: str,
        embedding_sha256: str,
        model_identifier: str = "speechbrain/spkrec-ecapa-voxceleb",
    ) -> VoiceProfile:
        """Create a new active voice profile, revoking any prior active profile."""
        # Deactivate any previous active profile for this user
        prior_active = await self.get_active_profile_by_user(user_id)
        if prior_active:
            prior_active.status = "REVOKED"
            prior_active.revoked_at = utc_now()
            prior_active.updated_at = utc_now()

        profile = VoiceProfile(
            user_id=user_id,
            status="ACTIVE",
            sample_count=sample_count,
            mean_pairwise_similarity=mean_pairwise_similarity,
            model_identifier=model_identifier,
            embedding_storage_path=embedding_storage_path,
            embedding_sha256=embedding_sha256,
        )
        return await self.add(profile)

    async def get_profile_by_id(self, profile_id: uuid.UUID) -> Optional[VoiceProfile]:
        """Fetch profile by UUID with preloaded enrollment samples."""
        stmt = (
            select(VoiceProfile)
            .where(VoiceProfile.id == profile_id)
            .options(selectinload(VoiceProfile.enrollment_records))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_profile_by_user(self, user_id: uuid.UUID) -> Optional[VoiceProfile]:
        """Fetch the current ACTIVE voice profile for a user."""
        stmt = (
            select(VoiceProfile)
            .where(
                VoiceProfile.user_id == user_id,
                VoiceProfile.status == "ACTIVE",
            )
            .options(selectinload(VoiceProfile.enrollment_records))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_profiles(
        self,
        user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[VoiceProfile]:
        """Fetch a paginated list of profiles ordered by created_at descending."""
        stmt = select(VoiceProfile).options(selectinload(VoiceProfile.enrollment_records))
        if user_id:
            stmt = stmt.where(VoiceProfile.user_id == user_id)
        stmt = stmt.order_by(desc(VoiceProfile.created_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_profile_status(
        self,
        profile_id: uuid.UUID,
        status: str,
    ) -> Optional[VoiceProfile]:
        """Update lifecycle status of a voice profile ('ACTIVE' or 'REVOKED')."""
        profile = await self.get_profile_by_id(profile_id)
        if not profile:
            return None

        upper_status = status.upper()
        profile.status = upper_status
        profile.updated_at = utc_now()
        if upper_status == "REVOKED":
            profile.revoked_at = utc_now()

        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def revoke_profile(self, profile_id: uuid.UUID) -> Optional[VoiceProfile]:
        """Revoke a voice profile."""
        return await self.update_profile_status(profile_id, "REVOKED")

    async def add_enrollment_record(
        self,
        profile_id: uuid.UUID,
        duration_sec: float,
        rms_energy: float,
        peak_amplitude: float,
        audio_format: str,
        snr_db: Optional[float] = None,
    ) -> EnrollmentRecord:
        """Record numerical acoustic metadata for an utterance used in profile aggregation."""
        record = EnrollmentRecord(
            profile_id=profile_id,
            duration_sec=duration_sec,
            rms_energy=rms_energy,
            peak_amplitude=peak_amplitude,
            snr_db=snr_db,
            audio_format=audio_format.upper(),
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)

        profile = await self.session.get(VoiceProfile, profile_id)
        if profile is not None:
            self.session.expire(profile, ["enrollment_records"])

        return record

