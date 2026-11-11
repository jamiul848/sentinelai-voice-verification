"""Unit and workflow tests for SpeakerVerificationService."""

from unittest.mock import MagicMock
import numpy as np
import pytest
import torch

from sentinelai.speaker.embedding import SpeakerEmbeddingExtractor, SpeakerEmbeddingResult
from sentinelai.verification.config import VerificationConfig
from sentinelai.verification.exceptions import (
    InvalidAudioInputError,
    VerificationScoringError,
)
from sentinelai.verification.schemas import VerificationStatus
from sentinelai.verification.service import SpeakerVerificationService


class TestVerificationService:
    """End-to-end service tests with controlled mock embeddings."""

    def test_verification_matching_speaker_returns_match(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """When candidate embedding aligns closely with reference (similarity >= 0.65), return MATCH."""
        # Enrolled Alice has reference vector mostly on first 10 dims.
        # Let's mock extractor to return an aligned vector for Alice's claimant audio
        aligned_vec = np.zeros(192, dtype=np.float32)
        aligned_vec[:10] = 0.95
        aligned_vec = aligned_vec / np.linalg.norm(aligned_vec)

        mock_result = SpeakerEmbeddingResult(
            embedding=aligned_vec,
            embedding_tensor=torch.from_numpy(aligned_vec),
            dimension=192,
            model_id="speechbrain/spkrec-ecapa-voxceleb",
            device="cpu",
            audio_duration_sec=1.5,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        verification_service.extractor.extract = MagicMock(return_value=mock_result)

        response = verification_service.verify_speaker(
            audio_input=valid_candidate_audio_sample,
            user_id="user_alice",
        )

        assert response.status == VerificationStatus.MATCH
        assert response.verified is True
        assert response.user_id == "user_alice"
        assert response.profile_id == "profile_alice_001"
        assert response.similarity_score is not None
        assert response.similarity_score >= 0.65
        assert "MATCH" in response.message
        assert response.processing_time_ms >= 0.0

    def test_verification_non_matching_speaker_returns_no_match(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """When candidate embedding diverges from reference (similarity < 0.65), return NO_MATCH."""
        # Alice's vector is on dims 0-10. Let's return vector on dims 50-60 (orthogonal, sim ~ 0.0)
        orthogonal_vec = np.zeros(192, dtype=np.float32)
        orthogonal_vec[50:60] = 1.0
        orthogonal_vec = orthogonal_vec / np.linalg.norm(orthogonal_vec)

        mock_result = SpeakerEmbeddingResult(
            embedding=orthogonal_vec,
            embedding_tensor=torch.from_numpy(orthogonal_vec),
            dimension=192,
            model_id="speechbrain/spkrec-ecapa-voxceleb",
            device="cpu",
            audio_duration_sec=1.5,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        verification_service.extractor.extract = MagicMock(return_value=mock_result)

        response = verification_service.verify_speaker(
            audio_input=valid_candidate_audio_sample,
            user_id="user_alice",
        )

        assert response.status == VerificationStatus.NO_MATCH
        assert response.verified is False
        assert response.similarity_score is not None
        assert response.similarity_score < 0.65
        assert "NO_MATCH" in response.message

    def test_verification_rejects_silent_and_corrupt_audio(
        self,
        verification_service: SpeakerVerificationService,
        silent_audio_sample: bytes,
        corrupt_audio_sample: bytes,
    ) -> None:
        """Silent and corrupted audio inputs must be rejected with InvalidAudioInputError."""
        # Silent audio
        with pytest.raises(InvalidAudioInputError, match="Candidate audio rejected"):
            verification_service.verify_speaker(
                audio_input=silent_audio_sample,
                user_id="user_alice",
            )

        # Corrupt audio
        with pytest.raises(InvalidAudioInputError, match="Candidate audio rejected"):
            verification_service.verify_speaker(
                audio_input=corrupt_audio_sample,
                user_id="user_alice",
            )

    def test_verification_embedding_dimension_mismatch(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Dimension mismatch between candidate embedding and profile raises VerificationScoringError."""
        vec_512 = np.ones(512, dtype=np.float32) / np.sqrt(512)
        mock_result = SpeakerEmbeddingResult(
            embedding=vec_512,
            embedding_tensor=torch.from_numpy(vec_512),
            dimension=512,
            model_id="speechbrain/spkrec-ecapa-voxceleb",
            device="cpu",
            audio_duration_sec=1.5,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        verification_service.extractor.extract = MagicMock(return_value=mock_result)

        with pytest.raises(VerificationScoringError, match="Embedding dimension mismatch"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                user_id="user_alice",
            )

    def test_verification_score_exposure_toggle(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """When expose_similarity_score is False, similarity_score must be None in public response."""
        verification_service.config.expose_similarity_score = False

        vec = np.zeros(192, dtype=np.float32)
        vec[:10] = 1.0
        vec = vec / np.linalg.norm(vec)

        mock_result = SpeakerEmbeddingResult(
            embedding=vec,
            embedding_tensor=torch.from_numpy(vec),
            dimension=192,
            model_id="speechbrain/spkrec-ecapa-voxceleb",
            device="cpu",
            audio_duration_sec=1.5,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        verification_service.extractor.extract = MagicMock(return_value=mock_result)

        response = verification_service.verify_speaker(
            audio_input=valid_candidate_audio_sample,
            user_id="user_alice",
        )

        assert response.verified is True
        assert response.similarity_score is None

    def test_verification_audit_logging_integrity(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Every verification transaction must record an audit event without biometric vectors."""
        assert len(verification_service.audit_logger.records) == 0

        vec = np.zeros(192, dtype=np.float32)
        vec[:10] = 1.0
        vec = vec / np.linalg.norm(vec)
        mock_result = SpeakerEmbeddingResult(
            embedding=vec,
            embedding_tensor=torch.from_numpy(vec),
            dimension=192,
            model_id="speechbrain/spkrec-ecapa-voxceleb",
            device="cpu",
            audio_duration_sec=1.5,
            extraction_timestamp="2026-11-11T00:00:00Z",
            normalized=True,
        )
        verification_service.extractor.extract = MagicMock(return_value=mock_result)

        verification_service.verify_speaker(
            audio_input=valid_candidate_audio_sample,
            user_id="user_alice",
        )

        records = verification_service.audit_logger.records
        assert len(records) == 1
        audit = records[0]
        assert audit.user_id == "user_alice"
        assert audit.profile_id == "profile_alice_001"
        assert audit.status == "MATCH"
        assert audit.verified is True
        assert audit.processing_time_ms >= 0.0

        # Guarantee no embedding or raw audio in audit record
        audit_dict = audit.to_dict()
        assert "embedding" not in audit_dict
        assert "reference_embedding" not in audit_dict
        assert "audio" not in audit_dict
