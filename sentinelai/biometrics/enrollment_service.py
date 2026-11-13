"""Sentinel Voice - Live Voice Biometric Enrollment Service.

Orchestrates the live enrollment pipeline:
1. Validates active biometric legal consent (GDPR / BIPA).
2. Enforces active profile concurrency guards (prevents duplicate active profiles).
3. Preprocesses multiple utterance recordings (enforces 16 kHz mono WAV/FLAC, duration, quality).
4. Extracts 192D speaker embeddings via the pretrained ECAPA-TDNN model.
5. Aggregates sample embeddings into an L2-normalized voiceprint centroid.
6. Encrypts the centroid using envelope encryption (unique DEK wrapped with master KEK).
7. Persists the encrypted vector container to isolated disk storage.
8. Writes profile and acoustic sample metadata to PostgreSQL.
9. Creates an immutable administrative audit log entry.
"""

import asyncio
import io
import logging
from pathlib import Path
from typing import Any, List, Optional, Union
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.audio.exceptions import SentinelAudioError
from sentinelai.audio.preprocessor import AudioPreprocessor
from sentinelai.biometrics.concurrency import get_inference_semaphore
from sentinelai.biometrics.exceptions import (
    ActiveProfileAlreadyExistsError,
    BiometricConsentRequiredError,
    InsufficientEnrollmentSamplesError,
    InvalidEnrollmentAudioError,
)
from sentinelai.biometrics.schemas import EnrollmentResponse, EnrollmentSampleMetadata
from sentinelai.biometrics.storage import BiometricStorageManager
from sentinelai.config import get_settings
from sentinelai.database.models.user import User
from sentinelai.database.models.voice_profile import VoiceProfile
from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.consent_repository import ConsentRepository
from sentinelai.database.repositories.profile_repository import ProfileRepository
from sentinelai.enrollment.aggregation import aggregate_embeddings
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor
from sentinelai.speaker.exceptions import EmbeddingExtractionError

logger = logging.getLogger(__name__)

MIN_ENROLLMENT_SAMPLES = 3
MAX_ENROLLMENT_SAMPLES = 10


class BiometricEnrollmentService:
    """High-level service coordinating multi-sample voice enrollment and cryptographic storage."""

    def __init__(
        self,
        session: AsyncSession,
        storage: Optional[BiometricStorageManager] = None,
        extractor: Optional[SpeakerEmbeddingExtractor] = None,
        preprocessor: Optional[AudioPreprocessor] = None,
    ) -> None:
        """Initialize the enrollment service with repositories and AI models.

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
        self.audit_repo = AuditRepository(session)

    async def _read_audio_bytes(self, audio_item: Any) -> tuple[bytes, str]:
        """Normalize various audio input formats into raw bytes and a source name."""
        data: bytes
        filename: str

        # FastAPI UploadFile
        if hasattr(audio_item, "read"):
            if callable(getattr(audio_item, "seek", None)):
                await audio_item.seek(0)
            data = await audio_item.read()
            filename = getattr(audio_item, "filename", "utterance.wav") or "utterance.wav"
        elif isinstance(audio_item, bytes):
            data = audio_item
            filename = "utterance.wav"
        elif isinstance(audio_item, (str, Path)):
            p = Path(audio_item)
            with open(p, "rb") as f:
                data = f.read()
            filename = p.name
        else:
            raise InvalidEnrollmentAudioError(f"Unsupported audio input type: {type(audio_item).__name__}")

        # Enforce maximum audio upload size
        if len(data) > self.settings.max_audio_upload_size_bytes:
            max_mb = self.settings.max_audio_upload_size_bytes // (1024 * 1024)
            raise InvalidEnrollmentAudioError(
                f"Audio recording '{filename}' ({len(data)} bytes) exceeds the maximum allowed size of {max_mb} MB."
            )

        return data, filename

    async def enroll_user(
        self,
        user: User,
        audio_files: List[Any],
        allow_replace: bool = False,
        client_ip: Optional[str] = None,
    ) -> EnrollmentResponse:
        """Execute full voiceprint enrollment for an authenticated user.

        Args:
            user: Authenticated User model instance.
            audio_files: List of audio items (UploadFile, bytes, or file paths).
            allow_replace: If True, automatically deactivates prior active profile (for re-enrollment).
            client_ip: Optional client IP address.

        Returns:
            EnrollmentResponse containing profile metadata and acoustic metrics.

        Raises:
            BiometricConsentRequiredError: If user lacks active legal consent.
            ActiveProfileAlreadyExistsError: If active profile exists and allow_replace=False.
            InsufficientEnrollmentSamplesError: If fewer than 3 valid samples provided.
            InvalidEnrollmentAudioError: If audio fails preprocessing or quality checks.
        """
        # Step 1: Legal Consent Verification
        has_consent = await self.consent_repo.has_active_consent(user.id)
        if not has_consent:
            raise BiometricConsentRequiredError(
                "Biometric voice enrollment requires explicit user consent (GDPR / BIPA). "
                "Please grant consent before proceeding."
            )

        # Step 2: Concurrency & Duplicate Active Profile Guard
        existing_profile = await self.profile_repo.get_active_profile_by_user(user.id)
        if existing_profile is not None and not allow_replace:
            raise ActiveProfileAlreadyExistsError(
                f"An active voice profile ({existing_profile.id}) is already registered. "
                "To replace it, please call the re-enrollment endpoint or revoke the current profile."
            )

        # Step 3: Sample Count Validation
        if len(audio_files) < MIN_ENROLLMENT_SAMPLES:
            raise InsufficientEnrollmentSamplesError(
                f"Voice enrollment requires at least {MIN_ENROLLMENT_SAMPLES} valid speech recordings. "
                f"Received {len(audio_files)}."
            )

        if len(audio_files) > MAX_ENROLLMENT_SAMPLES:
            audio_files = audio_files[:MAX_ENROLLMENT_SAMPLES]

        # Step 4: Preprocess Audio & Extract Embeddings
        embeddings = []
        samples_metadata: List[EnrollmentSampleMetadata] = []
        raw_samples_info = []

        for idx, item in enumerate(audio_files):
            data, filename = await self._read_audio_bytes(item)
            try:
                prep_result = self.preprocessor.process(data, source_id=filename)
            except SentinelAudioError as err:
                raise InvalidEnrollmentAudioError(
                    f"Sample {idx + 1} ({filename}) failed audio validation: {err.message}"
                ) from err
            except Exception as err:
                raise InvalidEnrollmentAudioError(
                    f"Sample {idx + 1} ({filename}) could not be preprocessed: {err}"
                ) from err

            try:
                # Bounded concurrency guard; offload CPU-bound inference to worker thread
                async with get_inference_semaphore():
                    emb_result = await asyncio.to_thread(
                        self.extractor.extract,
                        prep_result,
                        source_id=filename,
                    )
            except (EmbeddingExtractionError, Exception) as err:
                raise InvalidEnrollmentAudioError(
                    f"Sample {idx + 1} ({filename}) embedding extraction failed: {err}"
                ) from err

            embeddings.append(emb_result.embedding)

            audio_fmt = "WAV"
            if filename.lower().endswith(".flac"):
                audio_fmt = "FLAC"

            snr_val = getattr(prep_result.metrics, "snr_db", None)
            snr_db = round(float(snr_val), 2) if snr_val is not None else None

            meta = EnrollmentSampleMetadata(
                duration_sec=round(float(prep_result.duration_sec), 3),
                rms_energy=round(float(prep_result.rms_energy), 6),
                peak_amplitude=round(float(prep_result.peak_amplitude), 6),
                audio_format=audio_fmt,
                snr_db=snr_db,
            )
            samples_metadata.append(meta)
            raw_samples_info.append(
                {
                    "duration_sec": meta.duration_sec,
                    "rms_energy": meta.rms_energy,
                    "peak_amplitude": meta.peak_amplitude,
                    "audio_format": meta.audio_format,
                    "snr_db": meta.snr_db,
                }
            )

        # Step 5: Centroid Aggregation
        try:
            agg_result = aggregate_embeddings(embeddings)
        except Exception as err:
            raise InvalidEnrollmentAudioError(f"Failed to aggregate enrollment embeddings: {err}") from err

        centroid_vector = agg_result.reference_embedding
        mean_similarity = float(agg_result.mean_pairwise_similarity)
        sample_count = agg_result.sample_count

        # Step 6: Envelope Encrypt and Persist Biometric Vector Container
        profile_id = uuid.uuid4()
        storage_path, sha256_hash = self.storage.save_profile_vector(
            user_id=user.id,
            profile_id=profile_id,
            embedding=centroid_vector,
        )

        # Step 7: Record Database Entities
        model_id = self.settings.model_identifier
        profile = await self.profile_repo.create_profile(
            user_id=user.id,
            sample_count=sample_count,
            mean_pairwise_similarity=round(mean_similarity, 4),
            embedding_storage_path=storage_path,
            embedding_sha256=sha256_hash,
            model_identifier=model_id,
            profile_id=profile_id,
        )

        # Persist individual acoustic sample metadata records
        for s in raw_samples_info:
            await self.profile_repo.add_enrollment_record(
                profile_id=profile.id,
                duration_sec=s["duration_sec"],
                rms_energy=s["rms_energy"],
                peak_amplitude=s["peak_amplitude"],
                audio_format=s["audio_format"],
                snr_db=s["snr_db"],
            )

        # Step 8: Administrative Audit Log
        action_name = "VOICE_PROFILE_RE_ENROLLED" if allow_replace else "VOICE_PROFILE_ENROLLED"
        await self.audit_repo.create_audit_event(
            action=action_name,
            resource_type="voice_profile",
            resource_id=str(profile.id),
            actor_user_id=user.id,
            changes={
                "sample_count": sample_count,
                "mean_pairwise_similarity": round(mean_similarity, 4),
                "model_identifier": model_id,
                "storage_path": storage_path,
                "client_ip": client_ip,
            },
        )

        await self.session.commit()
        await self.session.refresh(profile)

        return EnrollmentResponse(
            profile_id=profile.id,
            user_id=profile.user_id,
            status=profile.status,
            sample_count=profile.sample_count,
            mean_pairwise_similarity=float(profile.mean_pairwise_similarity),
            model_identifier=profile.model_identifier,
            created_at=profile.created_at,
            samples=samples_metadata,
        )
