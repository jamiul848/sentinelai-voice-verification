"""Unit tests for Speaker Profile Validation during Verification."""

from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest

from sentinelai.enrollment.schemas import ProfileStatus, SpeakerProfile
from sentinelai.enrollment.storage import LocalFileProfileStorage
from sentinelai.verification.exceptions import (
    ProfileNotFoundError,
    ProfileRevokedError,
    VerificationError,
    VerificationScoringError,
)
from sentinelai.verification.service import SpeakerVerificationService


class TestProfileValidation:
    """Tests verifying active profile lookup and corruption/revocation handling."""

    def test_verify_nonexistent_profile_id_raises_not_found(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Attempting to verify against an unknown profile_id should raise ProfileNotFoundError."""
        with pytest.raises(ProfileNotFoundError, match="with ID 'profile_nonexistent' not found"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                profile_id="profile_nonexistent",
            )

    def test_verify_nonexistent_user_id_raises_not_found(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Attempting to verify against an unknown user_id should raise ProfileNotFoundError."""
        with pytest.raises(ProfileNotFoundError, match="No active enrolled speaker profile found"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                user_id="user_nonexistent",
            )

    def test_verify_revoked_profile_id_raises_revoked_error(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Attempting to verify against an enrolled profile that is REVOKED must raise ProfileRevokedError."""
        with pytest.raises(ProfileRevokedError, match="is REVOKED and cannot be used for verification"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                profile_id="profile_charlie_003",
            )

    def test_verify_user_with_revoked_profile_raises_revoked_error(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Attempting to verify user_charlie whose only profile is REVOKED must raise ProfileRevokedError."""
        with pytest.raises(ProfileRevokedError, match="have been revoked"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                user_id="user_charlie",
            )

    def test_verify_missing_both_identifiers_raises_verification_error(
        self,
        verification_service: SpeakerVerificationService,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """Providing neither user_id nor profile_id must raise VerificationError."""
        with pytest.raises(VerificationError, match="At least one of user_id or profile_id must be provided"):
            verification_service.verify_speaker(audio_input=valid_candidate_audio_sample)

    def test_profile_with_missing_reference_embedding_raises_scoring_error(
        self,
        verification_service: SpeakerVerificationService,
        verification_storage: LocalFileProfileStorage,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """If a stored profile lacks a reference embedding, VerificationScoringError must be raised."""
        corrupt_profile = SpeakerProfile(
            profile_id="profile_corrupt_no_emb",
            user_id="user_corrupt",
            reference_embedding=None,
            embedding_dimension=192,
            model_name="speechbrain/spkrec-ecapa-voxceleb",
            enrollment_sample_count=3,
            consent_status=True,
            profile_status=ProfileStatus.ACTIVE,
        )
        verification_storage.save_profile(corrupt_profile)

        with pytest.raises(VerificationScoringError, match="has no stored reference embedding"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                profile_id="profile_corrupt_no_emb",
            )

    def test_profile_with_nan_reference_embedding_raises_scoring_error(
        self,
        verification_service: SpeakerVerificationService,
        verification_storage: LocalFileProfileStorage,
        valid_candidate_audio_sample: bytes,
    ) -> None:
        """If a stored profile has NaN values in its reference embedding, raise VerificationScoringError."""
        nan_vec = np.ones(192, dtype=np.float32)
        nan_vec[5] = np.nan

        corrupt_profile = SpeakerProfile(
            profile_id="profile_corrupt_nan_emb",
            user_id="user_nan",
            reference_embedding=nan_vec,
            embedding_dimension=192,
            model_name="speechbrain/spkrec-ecapa-voxceleb",
            enrollment_sample_count=3,
            consent_status=True,
            profile_status=ProfileStatus.ACTIVE,
        )
        verification_storage.save_profile(corrupt_profile)

        with pytest.raises(VerificationScoringError, match="contains non-finite numbers"):
            verification_service.verify_speaker(
                audio_input=valid_candidate_audio_sample,
                profile_id="profile_corrupt_nan_emb",
            )
