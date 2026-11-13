"""Unit tests for the EnrollmentService orchestrator."""

from typing import List
import numpy as np
import pytest

from sentinelai.enrollment.exceptions import DuplicateEnrollmentError, ProfileNotFoundError
from sentinelai.enrollment.schemas import ProfileStatus, UserEnrollmentStatus
from sentinelai.enrollment.service import EnrollmentService


class TestEnrollmentService:
    """Test suite for enrollment lifecycle operations."""

    def test_enrollment_success(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Enroll new speaker from multiple recordings."""
        response = enrollment_service.enroll(
            user_id="user_test_001",
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
            metadata={"department": "Security Operations"},
        )

        assert response.success is True
        assert response.user_id == "user_test_001"
        assert response.sample_count == 3
        assert response.embedding_dimension == 192

        # Verify active profile can be retrieved
        profile = enrollment_service.get_speaker_profile(response.profile_id)
        assert profile.is_active is True
        assert profile.embedding_dimension == 192
        assert profile.reference_embedding is not None
        assert pytest.approx(float(np.linalg.norm(profile.reference_embedding)), abs=1e-5) == 1.0

    def test_public_profile_omits_embeddings(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Never expose actual biometric embeddings through public responses."""
        res = enrollment_service.enroll(
            user_id="user_privacy_test",
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
        )

        public_profile = enrollment_service.get_public_profile(res.profile_id)
        # Check dictionary representation: no embedding keys allowed
        d = public_profile.model_dump()
        assert "reference_embedding" not in d
        assert "individual_embeddings" not in d
        assert "embedding" not in d
        assert d["user_id"] == "user_privacy_test"
        assert d["status"] == ProfileStatus.ACTIVE

    def test_duplicate_enrollment_rejected(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Do not silently overwrite profile; reject duplicate enrollments."""
        enrollment_service.enroll(
            user_id="user_duplicate_test",
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
        )

        with pytest.raises(DuplicateEnrollmentError) as exc_info:
            enrollment_service.enroll(
                user_id="user_duplicate_test",
                audio_sources=valid_enrollment_audio_samples,
                consent=True,
            )
        assert "already has an active voice profile" in str(exc_info.value)

    def test_re_enrollment_workflow(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Allow an existing user to replace reference voice profile."""
        # 1. Initial enrollment
        initial_res = enrollment_service.enroll(
            user_id="user_reenroll_test",
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
        )
        old_profile_id = initial_res.profile_id

        # 2. Re-enrollment with new audio samples
        re_res = enrollment_service.re_enroll(
            user_id="user_reenroll_test",
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
        )

        assert re_res.success is True
        assert re_res.previous_profile_id == old_profile_id
        assert re_res.profile_id != old_profile_id

        # 3. Check old profile is revoked
        old_profile = enrollment_service.storage.get_profile_by_id(old_profile_id)
        assert old_profile is not None
        assert old_profile.profile_status == ProfileStatus.REVOKED
        assert "Superseded" in (old_profile.revocation_reason or "")

        # 4. Check new profile is active
        active_profile = enrollment_service.get_speaker_profile(re_res.profile_id)
        assert active_profile.is_active is True
        assert active_profile.profile_id == re_res.profile_id

    def test_enrollment_status_lifecycle(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Track enrollment status (NOT_ENROLLED -> ACTIVE -> REVOKED)."""
        uid = "lifecycle_user"

        # Initially NOT_ENROLLED
        st0 = enrollment_service.get_enrollment_status(uid)
        assert st0.status == UserEnrollmentStatus.NOT_ENROLLED

        # Enroll -> ACTIVE
        enroll_res = enrollment_service.enroll(
            user_id=uid,
            audio_sources=valid_enrollment_audio_samples,
            consent=True,
        )
        st1 = enrollment_service.get_enrollment_status(uid)
        assert st1.status == UserEnrollmentStatus.ACTIVE
        assert st1.profile_id == enroll_res.profile_id

        # Revoke -> REVOKED
        enrollment_service.revoke_profile(enroll_res.profile_id)
        st2 = enrollment_service.get_enrollment_status(uid)
        assert st2.status == UserEnrollmentStatus.REVOKED

