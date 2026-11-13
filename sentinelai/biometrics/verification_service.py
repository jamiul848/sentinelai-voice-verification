"""Sentinel Voice - Live Voice Biometric Speaker Verification Service.

Orchestrates the live verification pipeline:
1. Validates active biometric legal consent (GDPR / BIPA).
2. Retrieves the user's active enrolled voiceprint profile.
3. Decrypts and authenticates the reference vector container from secure storage.
4. Preprocesses probe audio (16 kHz mono WAV/FLAC, duration, quality).
5. Extracts probe embedding via pretrained ECAPA-TDNN model.
6. Computes directional cosine similarity on the unit hypersphere.
7. Dynamically retrieves the active calibrated decision threshold from PostgreSQL.
8. Evaluates MATCH vs. NO_MATCH decision.
9. Persists an immutable VerificationEvent transaction with latency and provenance.
10. Writes an audit log entry.
"""

import asyncio
import logging
from pathlib import Path
import time
from typing import Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.audio.exceptions import SentinelAudioError
from sentinelai.audio.preprocessor import AudioPreprocessor
from sentinelai.biometrics.concurrency import get_inference_semaphore
from sentinelai.biometrics.exceptions import (
    BiometricConsentRequiredError,
    InvalidEnrollmentAudioError,
    ProfileNotFoundError,
    ProfileRevokedError,
)
from sentinelai.biometrics.schemas import VerificationResponse
from sentinelai.biometrics.storage import BiometricStorageManager
from sentinelai.config import get_settings
from sentinelai.database.models.user import User
from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.consent_repository import ConsentRepository
from sentinelai.database.repositories.profile_repository import ProfileRepository
from sentinelai.database.repositories.threshold_repository import ThresholdRepository
from sentinelai.database.repositories.verification_repository import VerificationRepository
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.exceptions import EmbeddingExtractionError
from sentinelai.speaker.similarity import compute_cosine_similarity

logger = logging.getLogger(__name__)


class BiometricVerificationService:
    """High-level service executing end-to-end speaker verification."""

    def __init__(
        self,
        session: AsyncSession,
        storage: Optional[BiometricStorageManager] = None,
        extractor: Optional[SpeakerEmbeddingExtractor] = None,
        preprocessor: Optional[AudioPreprocessor] = None,
    ) -> None:
        """Initialize the verification service.

        Args:
            session: AsyncSession connected to PostgreSQL.
            storage: Optional BiometricStorageManager.
            extractor: Optional SpeakerEmbeddingExtractor.
            preprocessor: Optional AudioPreprocessor.
        """
        self.session = session
        self.settings = get_settings()
        self.storage = storage or BiometricStorageManager()
        self.extractor = extractor or SpeakerEmbeddingExtractor()
        self.preprocessor = preprocessor or AudioPreprocessor()

        self.consent_repo = ConsentRepository(session)
        self.profile_repo = ProfileRepository(session)
        self.threshold_repo = ThresholdRepository(session)
        self.verification_repo = VerificationRepository(session)
        self.audit_repo = AuditRepository(session)

    async def _read_audio_bytes(self, audio_item: Any) -> tuple[bytes, str]:
        """Normalize probe audio input format into raw bytes and a source name."""
        data: bytes
        filename: str

        if hasattr(audio_item, "read"):
            if callable(getattr(audio_item, "seek", None)):
                await audio_item.seek(0)
            data = await audio_item.read()
            filename = getattr(audio_item, "filename", "probe.wav") or "probe.wav"
        elif isinstance(audio_item, bytes):
            data = audio_item
            filename = "probe.wav"
        elif isinstance(audio_item, (str, Path)):
            p = Path(audio_item)
            with open(p, "rb") as f:
                data = f.read()
            filename = p.name
        else:
            raise InvalidEnrollmentAudioError(f"Unsupported audio input type: {type(audio_item).__name__}")

        if len(data) > self.settings.max_audio_upload_size_bytes:
            max_mb = self.settings.max_audio_upload_size_bytes // (1024 * 1024)
            raise InvalidEnrollmentAudioError(
                f"Probe audio '{filename}' ({len(data)} bytes) exceeds the maximum allowed size of {max_mb} MB."
            )

        return data, filename

    async def verify_user(
        self,
        user: User,
        audio_file: Any,
        client_ip: Optional[str] = None,
    ) -> VerificationResponse:
        """Verify a voice recording probe against the user's active enrolled voiceprint.

        Args:
            user: Authenticated User model instance.
            audio_file: Probe audio recording (UploadFile, bytes, or file path).
            client_ip: Optional client IP address.

        Returns:
            VerificationResponse detailing similarity, decision, threshold, and latency.

        Raises:
            BiometricConsentRequiredError: If user lacks active biometric consent.
            ProfileNotFoundError: If user has no active voice profile.
            ProfileRevokedError: If user profile is revoked.
            InvalidEnrollmentAudioError: If probe audio is invalid or degraded.
        """
        start_time = time.perf_counter()

        # Step 1: Legal Consent Verification
        has_consent = await self.consent_repo.has_active_consent(user.id)
        if not has_consent:
            raise BiometricConsentRequiredError(
                "Biometric verification requires explicit user consent (GDPR / BIPA). "
                "Please grant consent before submitting voice verification requests."
            )

        # Step 2: Retrieve Active Enrolled Voice Profile
        profile = await self.profile_repo.get_active_profile_by_user(user.id)
        if profile is None:
            raise ProfileNotFoundError(
                "No active voice profile found for this user. "
                "Please complete voice enrollment first."
            )

        if profile.status != "ACTIVE":
            raise ProfileRevokedError("Your voice profile is revoked and cannot be verified against.")

        # Step 3: Decrypt Reference Voiceprint Centroid
        ref_embedding = self.storage.load_profile_vector(
            user_id=user.id,
            profile_id=profile.id,
            storage_path=profile.embedding_storage_path,
            expected_sha256=profile.embedding_sha256,
        )

        # Step 4: Preprocess Probe Audio & Extract Probe Embedding
        data, filename = await self._read_audio_bytes(audio_file)
        try:
            prep_result = self.preprocessor.process(data, source_id=filename)
        except SentinelAudioError as err:
            raise InvalidEnrollmentAudioError(
                f"Probe audio ({filename}) failed acoustic validation: {err.message}"
            ) from err
        except Exception as err:
            raise InvalidEnrollmentAudioError(
                f"Probe audio ({filename}) could not be preprocessed: {err}"
            ) from err

        try:
            async with get_inference_semaphore():
                emb_result = await asyncio.to_thread(
                    self.extractor.extract,
                    prep_result,
                    source_id=filename,
                )
        except (EmbeddingExtractionError, Exception) as err:
            raise InvalidEnrollmentAudioError(
                f"Probe audio ({filename}) embedding extraction failed: {err}"
            ) from err

        probe_embedding = emb_result.embedding

        # Step 5: Compute Cosine Similarity
        similarity = float(compute_cosine_similarity(probe_embedding, ref_embedding))

        # Step 6: Dynamic Threshold Retrieval from PostgreSQL
        threshold_config = await self.threshold_repo.get_active_threshold(
            model_identifier=profile.model_identifier
        )
        if threshold_config is not None:
            applied_threshold = float(threshold_config.threshold_value)
            threshold_id = threshold_config.id
            threshold_version = threshold_config.version_tag
        else:
            # Fallback to application default threshold seed
            applied_threshold = float(self.settings.default_threshold)
            threshold_id = None
            threshold_version = "default_fallback"

        # Step 7: Evaluate Decision
        is_match = similarity >= applied_threshold
        decision = "MATCH" if is_match else "NO_MATCH"
        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Step 8: Persist Immutable VerificationEvent Transaction
        event = await self.verification_repo.create_verification_event(
            user_id=user.id,
            profile_id=profile.id,
            threshold_id=threshold_id,
            decision=decision,
            similarity_score=round(similarity, 6),
            applied_threshold=round(applied_threshold, 6),
            is_match=is_match,
            processing_time_ms=latency_ms,
            client_ip=client_ip,
        )

        # Step 9: Administrative Audit Log
        await self.audit_repo.create_audit_event(
            action="SPEAKER_VERIFIED",
            resource_type="verification_event",
            resource_id=str(event.id),
            actor_user_id=user.id,
            changes={
                "decision": decision,
                "is_match": is_match,
                "similarity_score": round(similarity, 6),
                "applied_threshold": round(applied_threshold, 6),
                "threshold_version": threshold_version,
                "processing_time_ms": latency_ms,
                "client_ip": client_ip,
            },
        )

        await self.session.commit()
        await self.session.refresh(event)

        return VerificationResponse(
            verification_id=event.id,
            decision=event.decision,
            is_match=event.is_match,
            similarity_score=float(event.similarity_score),
            applied_threshold=float(event.applied_threshold),
            processing_time_ms=float(event.processing_time_ms),
            model_identifier=profile.model_identifier,
            threshold_version=threshold_version,
            threshold_id=threshold_id,
            timestamp=event.created_at,
        )
