"""Enrollment Service Orchestrator.

Manages speaker registration, multi-utterance validation, embedding extraction,
profile creation, re-enrollment, and revocation.
"""

from datetime import datetime, timezone
import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import uuid
import numpy as np

from sentinelai.audio.exceptions import SentinelAudioError
from sentinelai.audio.preprocessor import AudioPreprocessor
from sentinelai.enrollment.aggregation import aggregate_embeddings
from sentinelai.enrollment.config import EnrollmentConfig
from sentinelai.enrollment.exceptions import (
    DuplicateEnrollmentError,
    EnrollmentConsentError,
    EnrollmentValidationError,
    ExcessiveRecordingsError,
    InsufficientRecordingsError,
    ProfileNotFoundError,
    ProfileRevokedError,
)
from sentinelai.enrollment.schemas import (
    EnrollmentResponse,
    EnrollmentStatusResponse,
    ProfileStatus,
    ReEnrollmentResponse,
    RevocationResponse,
    SpeakerProfile,
    SpeakerProfilePublic,
    UserEnrollmentStatus,
)
from sentinelai.enrollment.storage import LocalFileProfileStorage, ProfileStorageBackend
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.exceptions import SpeakerRecognitionError

logger = logging.getLogger(__name__)


class EnrollmentService:
    """Core domain service orchestrating speaker voice enrollment and lifecycle management."""

    def __init__(
        self,
        config: Optional[EnrollmentConfig] = None,
        storage: Optional[ProfileStorageBackend] = None,
        preprocessor: Optional[AudioPreprocessor] = None,
        extractor: Optional[SpeakerEmbeddingExtractor] = None,
    ) -> None:
        """Initialize the EnrollmentService.

        Args:
            config: Enrollment configuration settings.
            storage: Storage backend for profile records and biometric vectors.
            preprocessor: AudioPreprocessor instance for audio validation and resampling.
            extractor: SpeakerEmbeddingExtractor for ECAPA-TDNN feature extraction.
        """
        self.config = config or EnrollmentConfig()
        self.storage = storage or LocalFileProfileStorage(storage_dir=self.config.storage_dir)
        self.preprocessor = preprocessor or AudioPreprocessor()
        self.extractor = extractor or SpeakerEmbeddingExtractor()

    def _validate_user_id(self, user_id: str) -> str:
        """Sanitize and validate user identifier."""
        if not user_id or not isinstance(user_id, str):
            raise EnrollmentValidationError("user_id must be a non-empty string.")
        cleaned = user_id.strip()
        if len(cleaned) < 2 or len(cleaned) > 128:
            raise EnrollmentValidationError("user_id must be between 2 and 128 characters.")
        return cleaned

    def _process_and_extract_embeddings(
        self,
        audio_sources: List[Union[str, Path, bytes, io.BytesIO]],
        user_id: str,
    ) -> List[np.ndarray]:
        """Validate, preprocess, and extract embeddings for all submitted voice recordings."""
        count = len(audio_sources)

        if count < self.config.min_recordings:
            raise InsufficientRecordingsError(
                f"Enrollment requires at least {self.config.min_recordings} valid audio recordings, "
                f"but only {count} were provided.",
                count=count,
                min_required=self.config.min_recordings,
            )

        if count > self.config.max_recordings:
            raise ExcessiveRecordingsError(
                f"Enrollment permits at most {self.config.max_recordings} audio recordings, "
                f"but {count} were submitted.",
                count=count,
                max_allowed=self.config.max_recordings,
            )

        extracted_embeddings: List[np.ndarray] = []

        for idx, source in enumerate(audio_sources):
            source_label = f"recording_{idx + 1}_for_{user_id}"
            try:
                # 1. Preprocess audio (validates WAV format, mono, 16kHz, duration, and silence)
                prep_result = self.preprocessor.process(source, source_id=source_label)

                # 2. Extract ECAPA-TDNN embedding
                emb_result = self.extractor.extract(prep_result, source_id=source_label)
                extracted_embeddings.append(emb_result.embedding)

            except (SentinelAudioError, SpeakerRecognitionError) as exc:
                raise EnrollmentValidationError(
                    f"Voice recording {idx + 1} failed preprocessing or embedding extraction: {exc}"
                ) from exc
            except Exception as exc:
                raise EnrollmentValidationError(
                    f"Unexpected failure processing recording {idx + 1}: {exc}"
                ) from exc

        return extracted_embeddings

    def enroll(
        self,
        user_id: str,
        audio_sources: List[Union[str, Path, bytes, io.BytesIO]],
        consent: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnrollmentResponse:
        """Register a new speaker profile from multiple voice recordings.

        Args:
            user_id: Unique user identifier.
            audio_sources: List of audio recordings (file paths, byte buffers, or streams).
            consent: Explicit user consent confirmation.
            metadata: Optional dictionary of client metadata.

        Returns:
            EnrollmentResponse containing registration confirmation (omitting biometric vectors).

        Raises:
            EnrollmentConsentError: If consent is missing or False.
            DuplicateEnrollmentError: If the user already has an active enrolled profile.
            InsufficientRecordingsError: If fewer than min_recordings are provided.
            EnrollmentValidationError: If any recording fails validation checks.
        """
        clean_user_id = self._validate_user_id(user_id)

        # 1. Verify explicit biometric consent
        if self.config.require_explicit_consent and not consent:
            raise EnrollmentConsentError(
                "Biometric enrollment requires explicit positive user consent. "
                "Registration cannot proceed without consent."
            )

        # 2. Verify no active profile already exists for this user
        existing_profile = self.storage.get_active_profile_by_user_id(clean_user_id)
        if existing_profile is not None:
            raise DuplicateEnrollmentError(
                f"User '{clean_user_id}' already has an active voice profile (profile_id: "
                f"'{existing_profile.profile_id}'). Use the re-enrollment operation to update."
            )

        # 3. Preprocess audio recordings and extract individual embeddings
        embeddings = self._process_and_extract_embeddings(audio_sources, clean_user_id)

        # 4. Aggregate embeddings into L2-normalized reference centroid
        aggregation = aggregate_embeddings(embeddings)

        # 5. Build and persist speaker profile
        profile_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        profile_metadata = dict(metadata or {})
        profile_metadata.update({
            "intra_session_metrics": aggregation.metrics,
            "mean_pairwise_similarity": aggregation.mean_pairwise_similarity,
            "min_pairwise_similarity": aggregation.min_pairwise_similarity,
        })

        profile = SpeakerProfile(
            profile_id=profile_id,
            user_id=clean_user_id,
            reference_embedding=aggregation.reference_embedding,
            individual_embeddings=aggregation.individual_embeddings if self.config.retain_individual_embeddings else None,
            embedding_dimension=aggregation.dimension,
            model_name=self.extractor.config.model_source,
            model_version=None,
            enrollment_sample_count=len(embeddings),
            created_at=now,
            updated_at=now,
            consent_status=consent,
            profile_status=ProfileStatus.ACTIVE,
            metadata=profile_metadata,
        )

        self.storage.save_profile(profile)
        logger.info(f"Successfully enrolled voice profile '{profile_id}' for user '{clean_user_id}'.")

        return EnrollmentResponse(
            success=True,
            profile_id=profile_id,
            user_id=clean_user_id,
            sample_count=len(embeddings),
            embedding_dimension=aggregation.dimension,
            created_at=now.isoformat(),
            message="Voice profile successfully enrolled and stored.",
        )

    def re_enroll(
        self,
        user_id: str,
        audio_sources: List[Union[str, Path, bytes, io.BytesIO]],
        consent: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReEnrollmentResponse:
        """Re-enroll an existing user, revoking their previous profile and creating a fresh reference.

        Args:
            user_id: Unique user identifier.
            audio_sources: List of new audio recordings.
            consent: Explicit user consent confirmation.
            metadata: Optional dictionary of client metadata.

        Returns:
            ReEnrollmentResponse detailing the new profile and superseded profile IDs.
        """
        clean_user_id = self._validate_user_id(user_id)

        if self.config.require_explicit_consent and not consent:
            raise EnrollmentConsentError("Biometric re-enrollment requires explicit positive user consent.")

        # Find existing active profile if any
        prev_profile = self.storage.get_active_profile_by_user_id(clean_user_id)
        prev_profile_id = prev_profile.profile_id if prev_profile else "NONE"

        # If previous profile exists, revoke it and purge its old biometric vectors
        if prev_profile:
            prev_profile.profile_status = ProfileStatus.REVOKED
            prev_profile.revoked_at = datetime.now(timezone.utc)
            prev_profile.revocation_reason = "Superseded by re-enrollment."
            self.storage.update_profile(prev_profile)
            logger.info(f"Revoked superseded profile '{prev_profile.profile_id}' for user '{clean_user_id}'.")

        # Process new recordings
        embeddings = self._process_and_extract_embeddings(audio_sources, clean_user_id)
        aggregation = aggregate_embeddings(embeddings)

        new_profile_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        profile_metadata = dict(metadata or {})
        profile_metadata.update({
            "superseded_profile_id": prev_profile_id,
            "intra_session_metrics": aggregation.metrics,
        })

        new_profile = SpeakerProfile(
            profile_id=new_profile_id,
            user_id=clean_user_id,
            reference_embedding=aggregation.reference_embedding,
            individual_embeddings=aggregation.individual_embeddings if self.config.retain_individual_embeddings else None,
            embedding_dimension=aggregation.dimension,
            model_name=self.extractor.config.model_source,
            model_version=None,
            enrollment_sample_count=len(embeddings),
            created_at=now,
            updated_at=now,
            consent_status=consent,
            profile_status=ProfileStatus.ACTIVE,
            metadata=profile_metadata,
        )

        self.storage.save_profile(new_profile)
        logger.info(f"Successfully re-enrolled user '{clean_user_id}' with new profile '{new_profile_id}'.")

        return ReEnrollmentResponse(
            success=True,
            profile_id=new_profile_id,
            previous_profile_id=prev_profile_id,
            user_id=clean_user_id,
            sample_count=len(embeddings),
            embedding_dimension=aggregation.dimension,
            updated_at=now.isoformat(),
            message="Voice profile successfully updated and previous profile superseded.",
        )

    def revoke_profile(self, identifier: str, reason: Optional[str] = None) -> RevocationResponse:
        """Revoke a speaker profile and purge its biometric embedding vectors from storage.

        Args:
            identifier: Profile ID or user ID.
            reason: Optional justification for revocation.

        Returns:
            RevocationResponse confirming status and timestamp.

        Raises:
            ProfileNotFoundError: If no matching profile exists.
        """
        # Look up by profile_id first, then active profile by user_id
        profile = self.storage.get_profile_by_id(identifier)
        if profile is None:
            profile = self.storage.get_active_profile_by_user_id(identifier)

        if profile is None:
            raise ProfileNotFoundError(f"No profile found matching identifier '{identifier}'.")

        now = datetime.now(timezone.utc)
        profile.profile_status = ProfileStatus.REVOKED
        profile.revoked_at = now
        profile.revocation_reason = reason or "User requested revocation."

        # Updating profile purges the biometric embedding file from storage
        self.storage.update_profile(profile)
        logger.info(f"Revoked profile '{profile.profile_id}' for user '{profile.user_id}'.")

        return RevocationResponse(
            success=True,
            profile_id=profile.profile_id,
            user_id=profile.user_id,
            status=ProfileStatus.REVOKED,
            revoked_at=now.isoformat(),
            reason=profile.revocation_reason,
            message="Voice profile revoked and biometric vectors purged from storage.",
        )

    def get_public_profile(self, identifier: str) -> SpeakerProfilePublic:
        """Retrieve the public view of a profile by profile ID or active user ID.

        Args:
            identifier: Profile ID or user ID.

        Returns:
            SpeakerProfilePublic schema (strictly excluding embeddings).

        Raises:
            ProfileNotFoundError: If profile does not exist.
        """
        profile = self.storage.get_profile_by_id(identifier)
        if profile is None:
            profile = self.storage.get_active_profile_by_user_id(identifier)

        if profile is None:
            raise ProfileNotFoundError(f"Profile '{identifier}' not found.")

        return profile.to_public()

    def get_speaker_profile(self, identifier: str) -> SpeakerProfile:
        """Internal retrieval of full domain profile (for verification engine).

        Args:
            identifier: Profile ID or user ID.

        Returns:
            SpeakerProfile domain model.

        Raises:
            ProfileNotFoundError: If profile does not exist.
            ProfileRevokedError: If profile is revoked and cannot be used for verification.
        """
        profile = self.storage.get_profile_by_id(identifier)
        if profile is None:
            profile = self.storage.get_active_profile_by_user_id(identifier)

        if profile is None:
            raise ProfileNotFoundError(f"Profile '{identifier}' not found.")

        if not profile.is_active:
            raise ProfileRevokedError(
                f"Profile '{profile.profile_id}' is REVOKED and unavailable for verification."
            )

        return profile

    def get_enrollment_status(self, user_id: str) -> EnrollmentStatusResponse:
        """Check enrollment status for a given user identifier.

        Args:
            user_id: Unique user identifier.

        Returns:
            EnrollmentStatusResponse indicating ACTIVE, REVOKED, or NOT_ENROLLED.
        """
        clean_user_id = self._validate_user_id(user_id)

        active = self.storage.get_active_profile_by_user_id(clean_user_id)
        if active:
            return EnrollmentStatusResponse(
                user_id=clean_user_id,
                status=UserEnrollmentStatus.ACTIVE,
                profile_id=active.profile_id,
                sample_count=active.enrollment_sample_count,
                updated_at=active.updated_at.isoformat(),
            )

        all_profiles = self.storage.get_profiles_by_user_id(clean_user_id)
        if all_profiles:
            latest = all_profiles[0]
            return EnrollmentStatusResponse(
                user_id=clean_user_id,
                status=UserEnrollmentStatus.REVOKED,
                profile_id=latest.profile_id,
                sample_count=latest.enrollment_sample_count,
                updated_at=latest.updated_at.isoformat(),
            )

        return EnrollmentStatusResponse(
            user_id=clean_user_id,
            status=UserEnrollmentStatus.NOT_ENROLLED,
            profile_id=None,
            sample_count=None,
            updated_at=None,
        )

