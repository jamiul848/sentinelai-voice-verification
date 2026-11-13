"""Sentinel Voice - Biometric Voice Profile & Verification History Management Service.

Coordinates profile lifecycle workflows:
1. Retrieval of active profile metadata and constituent acoustic samples.
2. Chronological profile version history.
3. Explicit re-enrollment with automatic previous container shredding.
4. Voiceprint revocation with multi-pass vector container erasure.
5. Filterable, paginated verification audit history queries.
"""

from datetime import datetime
import logging
from typing import Any, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.biometrics.enrollment_service import BiometricEnrollmentService
from sentinelai.biometrics.exceptions import ProfileNotFoundError
from sentinelai.biometrics.schemas import (
    EnrollmentSampleMetadata,
    ProfileRevocationResponse,
    ReEnrollmentResponse,
    VerificationHistoryItem,
    VerificationHistoryResponse,
    VoiceProfileDetailResponse,
    VoiceProfileResponse,
)
from sentinelai.biometrics.storage import BiometricStorageManager
from sentinelai.database.models.user import User
from sentinelai.database.models.voice_profile import VoiceProfile
from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.profile_repository import ProfileRepository
from sentinelai.database.repositories.verification_repository import VerificationRepository

logger = logging.getLogger(__name__)


class BiometricProfileService:
    """Manages voice profile states, re-enrollments, revocations, and history."""

    def __init__(
        self,
        session: AsyncSession,
        storage: Optional[BiometricStorageManager] = None,
        enrollment_service: Optional[BiometricEnrollmentService] = None,
    ) -> None:
        """Initialize the profile management service.

        Args:
            session: AsyncSession connected to PostgreSQL.
            storage: Optional BiometricStorageManager.
            enrollment_service: Optional BiometricEnrollmentService.
        """
        self.session = session
        self.storage = storage or BiometricStorageManager()
        self.enrollment_service = enrollment_service or BiometricEnrollmentService(
            session=session,
            storage=self.storage,
        )
        self.profile_repo = ProfileRepository(session)
        self.verification_repo = VerificationRepository(session)
        self.audit_repo = AuditRepository(session)

    def _to_profile_response(self, profile: VoiceProfile) -> VoiceProfileResponse:
        """Map VoiceProfile ORM model to VoiceProfileResponse schema."""
        return VoiceProfileResponse(
            id=profile.id,
            user_id=profile.user_id,
            status=profile.status,
            sample_count=profile.sample_count,
            mean_pairwise_similarity=float(profile.mean_pairwise_similarity),
            model_identifier=profile.model_identifier,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            revoked_at=profile.revoked_at,
        )

    async def get_active_profile(self, user_id: uuid.UUID) -> VoiceProfileDetailResponse:
        """Retrieve active voice profile metadata and acoustic enrollment sample records.

        Args:
            user_id: User UUID.

        Returns:
            VoiceProfileDetailResponse containing profile and sample metadata.

        Raises:
            ProfileNotFoundError: If no active profile exists.
        """
        profile = await self.profile_repo.get_active_profile_by_user(user_id)
        if profile is None:
            raise ProfileNotFoundError("No active voice profile registered for this account.")

        samples = [
            EnrollmentSampleMetadata(
                duration_sec=float(r.duration_sec),
                rms_energy=float(r.rms_energy),
                peak_amplitude=float(r.peak_amplitude),
                audio_format=r.audio_format,
                snr_db=float(r.snr_db) if r.snr_db is not None else None,
            )
            for r in (profile.enrollment_records or [])
        ]

        return VoiceProfileDetailResponse(
            id=profile.id,
            user_id=profile.user_id,
            status=profile.status,
            sample_count=profile.sample_count,
            mean_pairwise_similarity=float(profile.mean_pairwise_similarity),
            model_identifier=profile.model_identifier,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            revoked_at=profile.revoked_at,
            enrollment_records=samples,
        )

    async def get_profile_history(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> List[VoiceProfileResponse]:
        """Fetch all historical profiles (ACTIVE and REVOKED) for the user.

        Args:
            user_id: User UUID.
            skip: Offset.
            limit: Limit.

        Returns:
            List of VoiceProfileResponse records.
        """
        profiles = await self.profile_repo.list_profiles(user_id=user_id, skip=skip, limit=limit)
        return [self._to_profile_response(p) for p in profiles]

    async def re_enroll(
        self,
        user: User,
        audio_files: List[Any],
        client_ip: Optional[str] = None,
    ) -> ReEnrollmentResponse:
        """Explicitly re-enroll a user's voiceprint, shredding the prior container.

        Args:
            user: Authenticated user.
            audio_files: List of audio recordings.
            client_ip: Optional client IP.

        Returns:
            ReEnrollmentResponse with new profile ID and previous profile ID.
        """
        # Step 1: Identify and shred prior active container if present
        prior_profile = await self.profile_repo.get_active_profile_by_user(user.id)
        prior_id: Optional[uuid.UUID] = None
        if prior_profile is not None:
            prior_id = prior_profile.id
            self.storage.delete_profile_vector(
                user_id=user.id,
                profile_id=prior_profile.id,
                storage_path=prior_profile.embedding_storage_path,
            )
            await self.profile_repo.revoke_profile(prior_profile.id)

        # Step 2: Enroll new profile
        enroll_res = await self.enrollment_service.enroll_user(
            user=user,
            audio_files=audio_files,
            allow_replace=True,
            client_ip=client_ip,
        )

        return ReEnrollmentResponse(
            profile_id=enroll_res.profile_id,
            previous_profile_id=prior_id,
            status=enroll_res.status,
            sample_count=enroll_res.sample_count,
            mean_pairwise_similarity=enroll_res.mean_pairwise_similarity,
            message="Voiceprint re-enrollment successful. Previous profile was revoked and shredded.",
        )

    async def revoke_profile(
        self,
        user: User,
        client_ip: Optional[str] = None,
    ) -> ProfileRevocationResponse:
        """Revoke active voice profile and shred the encrypted vector container from disk.

        Args:
            user: Authenticated user.
            client_ip: Optional client IP.

        Returns:
            ProfileRevocationResponse confirming revocation and erasure.

        Raises:
            ProfileNotFoundError: If user has no active profile.
        """
        profile = await self.profile_repo.get_active_profile_by_user(user.id)
        if profile is None:
            raise ProfileNotFoundError("No active voice profile to revoke.")

        # Cryptographically shred the vector file
        self.storage.delete_profile_vector(
            user_id=user.id,
            profile_id=profile.id,
            storage_path=profile.embedding_storage_path,
        )

        # Update database status
        updated_profile = await self.profile_repo.revoke_profile(profile.id)
        revoked_at = updated_profile.revoked_at if updated_profile else datetime.utcnow()

        # Record audit log
        await self.audit_repo.create_audit_event(
            action="VOICE_PROFILE_REVOKED",
            resource_type="voice_profile",
            resource_id=str(profile.id),
            actor_user_id=user.id,
            changes={"revoked_at": str(revoked_at), "client_ip": client_ip},
        )

        await self.session.commit()

        return ProfileRevocationResponse(
            profile_id=profile.id,
            status="REVOKED",
            revoked_at=revoked_at,
            message="Voice profile revoked and biometric vector shredded from storage.",
        )

    async def get_verification_history(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        decision: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        order: str = "desc",
    ) -> VerificationHistoryResponse:
        """Fetch paginated, filterable verification transaction events for the user.

        Args:
            user_id: User UUID.
            skip: Pagination offset.
            limit: Page size limit.
            decision: Filter by 'MATCH' or 'NO_MATCH'.
            start_date: Earliest event timestamp.
            end_date: Latest event timestamp.
            order: 'desc' or 'asc'.

        Returns:
            VerificationHistoryResponse containing transactions and total count.
        """
        events = await self.verification_repo.get_user_verification_history(
            user_id=user_id,
            skip=skip,
            limit=limit,
            decision=decision,
            start_date=start_date,
            end_date=end_date,
            order=order,
        )

        items = [
            VerificationHistoryItem(
                id=e.id,
                decision=e.decision,
                is_match=e.is_match,
                similarity_score=float(e.similarity_score),
                applied_threshold=float(e.applied_threshold),
                processing_time_ms=float(e.processing_time_ms),
                created_at=e.created_at,
                threshold_id=e.threshold_id,
                client_ip=e.client_ip,
            )
            for e in events
        ]

        # For total count, we can check length or query all
        total = len(items)  # At minimum length of retrieved page
        if len(items) == limit or skip > 0:
            # Query all without pagination for exact total count
            all_events = await self.verification_repo.get_user_verification_history(
                user_id=user_id,
                skip=0,
                limit=10000,
                decision=decision,
                start_date=start_date,
                end_date=end_date,
                order=order,
            )
            total = len(all_events)

        return VerificationHistoryResponse(
            total=total,
            skip=skip,
            limit=limit,
            items=items,
        )

