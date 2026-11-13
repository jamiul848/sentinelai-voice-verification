"""Unit tests for speaker profile revocation and biometric data purging."""

from pathlib import Path
from typing import List
import pytest

from sentinelai.enrollment.exceptions import ProfileNotFoundError, ProfileRevokedError
from sentinelai.enrollment.schemas import ProfileStatus, UserEnrollmentStatus
from sentinelai.enrollment.service import EnrollmentService


class TestProfileRevocation:
    """Test suite covering profile revocation, verification gating, and biometric purging."""

    def test_profile_revocation_success(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Revoke an enrolled profile and record revocation event."""
        # Enroll user first
        enroll_res = enrollment_service.enroll(
            user_id="alice_revocation_test",
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
        )
        profile_id = enroll_res.profile_id

        # Verify biometric embedding file initially exists on disk
        emb_file = enrollment_service.storage.storage_dir / f"{profile_id}.emb.npz"
        assert emb_file.exists()

        # Revoke profile
        rev_res = enrollment_service.revoke_profile(profile_id, reason="User exercised right to be forgotten.")
        assert rev_res.success is True
        assert rev_res.profile_id == profile_id
        assert rev_res.status == ProfileStatus.REVOKED

        # Requirement: Biometric data must be deleted according to retention policy
        assert not emb_file.exists(), "Biometric embedding file must be purged upon revocation."

        # Verify status endpoint reports REVOKED
        status_res = enrollment_service.get_enrollment_status("alice_revocation_test")
        assert status_res.status == UserEnrollmentStatus.REVOKED
        assert status_res.profile_id == profile_id

    def test_revoked_profile_unavailable_for_verification(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Revoked profile must not be available for future verification."""
        enroll_res = enrollment_service.enroll(
            user_id="bob_revocation_test",
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
        )
        profile_id = enroll_res.profile_id
        enrollment_service.revoke_profile(profile_id)

        # Attempting internal domain retrieval for verification must raise ProfileRevokedError
        with pytest.raises(ProfileRevokedError) as exc_info:
            enrollment_service.get_speaker_profile(profile_id)
        assert "REVOKED and unavailable" in str(exc_info.value)

    def test_revoke_nonexistent_profile_raises_error(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Verify revoking a non-existent ID raises ProfileNotFoundError."""
        with pytest.raises(ProfileNotFoundError):
            enrollment_service.revoke_profile("non_existent_profile_id_123")

