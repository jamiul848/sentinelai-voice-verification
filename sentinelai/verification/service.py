"""Speaker Verification Service Orchestrator.

Coordinates identity retrieval, audio preprocessing, ECAPA-TDNN feature extraction,
cosine similarity scoring, threshold evaluation, and privacy-safe audit logging.
"""

from datetime import datetime, timezone
import io
from pathlib import Path
import time
from typing import Any, Dict, Optional, Union
import uuid
import numpy as np
import torch

from sentinelai.audio.exceptions import SentinelAudioError
from sentinelai.enrollment.schemas import ProfileStatus, SpeakerProfile
from sentinelai.enrollment.storage import LocalFileProfileStorage, ProfileStorageBackend
from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor, SpeakerEmbeddingResult
from sentinelai.speaker.exceptions import (
    EmbeddingExtractionError,
    InvalidEmbeddingError,
    SpeakerRecognitionError,
)
from sentinelai.verification.audit import AuditLoggerBackend, AuditRecord, JsonLinesAuditLogger
from sentinelai.verification.config import VerificationConfig
from sentinelai.verification.exceptions import (
    InvalidAudioInputError,
    ProfileNotFoundError,
    ProfileRevokedError,
    VerificationError,
    VerificationScoringError,
)
from sentinelai.verification.schemas import VerificationResponse, VerificationStatus
from sentinelai.verification.scoring import compute_verification_score
from sentinelai.verification.threshold import VerificationThreshold


class SpeakerVerificationService:
    """Core domain service for 1:1 speaker identity verification."""

    def __init__(
        self,
        config: Optional[VerificationConfig] = None,
        extractor: Optional[SpeakerEmbeddingExtractor] = None,
        storage: Optional[ProfileStorageBackend] = None,
        audit_logger: Optional[AuditLoggerBackend] = None,
    ) -> None:
        """Initialize the verification service with its dependencies.

        Args:
            config: Verification configuration settings.
            extractor: Pretrained ECAPA-TDNN embedding extractor instance.
            storage: Speaker profile storage backend.
            audit_logger: Audit logger backend for recording verification events.
        """
        self.config = config or VerificationConfig()
        self.extractor = extractor or SpeakerEmbeddingExtractor()
        self.storage = storage or LocalFileProfileStorage(storage_dir=self.config.storage_dir)

        if audit_logger is not None:
            self.audit_logger = audit_logger
        elif self.config.audit_log_path is not None:
            self.audit_logger = JsonLinesAuditLogger(log_path=self.config.audit_log_path)
        else:
            self.audit_logger = None

        self.threshold = VerificationThreshold(
            threshold_value=self.config.threshold_value,
            version=self.config.threshold_version,
        )

    def _get_active_profile(
        self,
        user_id: Optional[str] = None,
        profile_id: Optional[str] = None,
    ) -> SpeakerProfile:
        """Retrieve and validate the active enrolled speaker profile.

        Args:
            user_id: User identifier.
            profile_id: Specific profile identifier.

        Returns:
            Active SpeakerProfile with valid reference embedding.

        Raises:
            VerificationError: If neither identifier is provided.
            ProfileNotFoundError: If no matching profile exists.
            ProfileRevokedError: If profile status is REVOKED.
            VerificationScoringError: If stored reference embedding is missing or corrupted.
        """
        if not user_id and not profile_id:
            raise VerificationError("At least one of user_id or profile_id must be provided.")

        profile: Optional[SpeakerProfile] = None

        if profile_id:
            profile = self.storage.get_profile_by_id(profile_id)
            if profile is None:
                raise ProfileNotFoundError(f"Speaker profile with ID '{profile_id}' not found.")
        elif user_id:
            profile = self.storage.get_active_profile_by_user_id(user_id)
            if profile is None:
                # Check if user has revoked profiles to give informative error
                existing = self.storage.get_profiles_by_user_id(user_id)
                if any(p.profile_status == ProfileStatus.REVOKED for p in existing):
                    raise ProfileRevokedError(f"All enrolled profiles for user '{user_id}' have been revoked.")
                raise ProfileNotFoundError(f"No active enrolled speaker profile found for user '{user_id}'.")

        assert profile is not None

        # Validate lifecycle status
        if profile.profile_status == ProfileStatus.REVOKED:
            raise ProfileRevokedError(
                f"Speaker profile '{profile.profile_id}' for user '{profile.user_id}' is REVOKED "
                "and cannot be used for verification."
            )

        # Validate reference embedding integrity
        if profile.reference_embedding is None:
            raise VerificationScoringError(
                f"Enrolled profile '{profile.profile_id}' has no stored reference embedding."
            )

        ref_emb = profile.reference_embedding
        if not isinstance(ref_emb, np.ndarray) or ref_emb.size == 0:
            raise VerificationScoringError(
                f"Enrolled profile '{profile.profile_id}' reference embedding is corrupted or empty."
            )

        if np.isnan(ref_emb).any() or np.isinf(ref_emb).any():
            raise VerificationScoringError(
                f"Enrolled profile '{profile.profile_id}' reference embedding contains non-finite numbers."
            )

        return profile

    def verify_speaker(
        self,
        audio_input: Union[str, Path, bytes, io.BytesIO, torch.Tensor],
        user_id: Optional[str] = None,
        profile_id: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationResponse:
        """Perform 1:1 speaker verification against an enrolled reference profile.

        Workflow:
            1. Validate claimed identity and load reference profile.
            2. Validate and preprocess candidate audio input.
            3. Extract candidate ECAPA-TDNN embedding.
            4. Compute directional cosine similarity with reference embedding.
            5. Evaluate score against configured decision threshold.
            6. Emit privacy-safe audit record.
            7. Return structured public verification response.

        Args:
            audio_input: WAV file path, raw audio bytes, BytesIO stream, or preprocessed tensor.
            user_id: Claimed user identifier.
            profile_id: Specific enrolled profile identifier.
            request_metadata: Non-biometric diagnostic or contextual metadata.

        Returns:
            VerificationResponse indicating MATCH or NO_MATCH.

        Raises:
            ProfileNotFoundError: If claimed profile is missing.
            ProfileRevokedError: If profile is revoked.
            InvalidAudioInputError: If candidate audio is empty, corrupted, silent, or invalid.
            VerificationScoringError: If embedding dimensions or values are invalid.
            VerificationError: For other verification errors.
        """
        start_time = time.perf_counter()
        verification_id = str(uuid.uuid4())
        meta = request_metadata or {}
        resolved_user_id = user_id or "unknown"
        resolved_profile_id = profile_id or "unknown"

        # 1. Retrieve and validate active enrolled profile
        profile = self._get_active_profile(user_id=user_id, profile_id=profile_id)
        resolved_user_id = profile.user_id
        resolved_profile_id = profile.profile_id

        # 2. Extract ECAPA-TDNN embedding from candidate audio
        try:
            claimant_result: SpeakerEmbeddingResult = self.extractor.extract(
                source=audio_input,
                source_id=f"claimant_{resolved_user_id}_{verification_id[:8]}",
            )
        except SentinelAudioError as exc:
            self._log_audit(
                verification_id=verification_id,
                user_id=resolved_user_id,
                profile_id=resolved_profile_id,
                status=VerificationStatus.INVALID_AUDIO.value,
                verified=False,
                start_time=start_time,
                metadata=meta,
            )
            raise InvalidAudioInputError(f"Candidate audio rejected: {exc}") from exc
        except (SpeakerRecognitionError, InvalidEmbeddingError, EmbeddingExtractionError) as exc:
            self._log_audit(
                verification_id=verification_id,
                user_id=resolved_user_id,
                profile_id=resolved_profile_id,
                status=VerificationStatus.VERIFICATION_ERROR.value,
                verified=False,
                start_time=start_time,
                metadata=meta,
            )
            raise VerificationError(f"Embedding extraction failed: {exc}") from exc

        # 3. Dimensional compatibility check
        ref_dim = profile.embedding_dimension
        claimant_dim = claimant_result.dimension
        if ref_dim != claimant_dim:
            self._log_audit(
                verification_id=verification_id,
                user_id=resolved_user_id,
                profile_id=resolved_profile_id,
                status=VerificationStatus.VERIFICATION_ERROR.value,
                verified=False,
                start_time=start_time,
                metadata=meta,
            )
            raise VerificationScoringError(
                f"Embedding dimension mismatch: enrolled profile has dimension {ref_dim}, "
                f"but claimant audio produced {claimant_dim} dimensions."
            )

        # 4. Compute directional cosine similarity
        score = compute_verification_score(
            reference_embedding=profile.reference_embedding,
            claimant_embedding=claimant_result.embedding,
        )

        # 5. Evaluate against verification decision threshold
        is_verified = self.threshold.is_match(score)
        status = VerificationStatus.MATCH if is_verified else VerificationStatus.NO_MATCH
        processing_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 6. Record privacy-safe audit event
        self._log_audit(
            verification_id=verification_id,
            user_id=resolved_user_id,
            profile_id=resolved_profile_id,
            status=status.value,
            verified=is_verified,
            start_time=start_time,
            metadata=meta,
        )

        # 7. Formulate public response (score exposed only if configured)
        message = (
            f"Speaker identity verified successfully (MATCH) against profile '{resolved_profile_id}'."
            if is_verified
            else f"Speaker verification rejected (NO_MATCH) against profile '{resolved_profile_id}'."
        )

        return VerificationResponse(
            verification_id=verification_id,
            user_id=resolved_user_id,
            profile_id=resolved_profile_id,
            status=status,
            verified=is_verified,
            similarity_score=round(score, 4) if self.config.expose_similarity_score else None,
            threshold_version=self.threshold.version,
            model_name=claimant_result.model_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=processing_ms,
            message=message,
        )

    def _log_audit(
        self,
        verification_id: str,
        user_id: str,
        profile_id: str,
        status: str,
        verified: bool,
        start_time: float,
        metadata: Dict[str, Any],
    ) -> None:
        """Internal helper to emit privacy-safe audit records."""
        if self.audit_logger is None:
            return

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        record = AuditRecord(
            verification_id=verification_id,
            user_id=user_id,
            profile_id=profile_id,
            status=status,
            verified=verified,
            threshold_version=self.threshold.version,
            model_name=getattr(self.extractor.config, "model_source", "speechbrain/spkrec-ecapa-voxceleb"),
            timestamp=datetime.now(timezone.utc).isoformat(),
            processing_time_ms=duration_ms,
            metadata={k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))},
        )
        try:
            self.audit_logger.log_verification(record)
        except Exception:
            # Audit logging failures should not crash verification return unless critical
            pass
