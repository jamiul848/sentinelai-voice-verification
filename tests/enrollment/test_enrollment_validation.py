"""Unit tests for enrollment request validation, recording quotas, and consent enforcement."""

from typing import List
import pytest

from sentinelai.enrollment.config import EnrollmentConfig
from sentinelai.enrollment.exceptions import (
    EnrollmentConsentError,
    EnrollmentValidationError,
    ExcessiveRecordingsError,
    InsufficientRecordingsError,
)
from sentinelai.enrollment.service import EnrollmentService
from tests.enrollment.conftest import create_synthetic_wav_bytes


class TestEnrollmentValidation:
    """Test suite covering input sanity, quotas, consent, and audio quality checks."""

    def test_missing_consent_raises_error(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Enrollment strictly requires positive biometric consent."""
        with pytest.raises(EnrollmentConsentError) as exc_info:
            enrollment_service.enroll(
                user_id="alice_test",
                audio_sources=valid_enrollment_audio_samples,
                consent=False,
            )
        assert "explicit positive user consent" in str(exc_info.value)

    def test_insufficient_recordings_raises_error(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Require at least min_recordings (default: 3) for a profile."""
        two_recordings = valid_enrollment_audio_samples[:2]
        with pytest.raises(InsufficientRecordingsError) as exc_info:
            enrollment_service.enroll(
                user_id="alice_test",
                audio_sources=two_recordings,
                consent=True,
            )
        assert exc_info.value.count == 2
        assert exc_info.value.min_required == 3

    def test_excessive_recordings_raises_error(
        self,
        enrollment_service: EnrollmentService,
    ) -> None:
        """Requirement: Reject requests exceeding max_recordings limit."""
        # Service configured with max_recordings=5 in conftest
        six_recordings = [create_synthetic_wav_bytes(freq_hz=400 + i * 20) for i in range(6)]
        with pytest.raises(ExcessiveRecordingsError) as exc_info:
            enrollment_service.enroll(
                user_id="alice_test",
                audio_sources=six_recordings,
                consent=True,
            )
        assert exc_info.value.count == 6
        assert exc_info.value.max_allowed == 5

    def test_corrupted_audio_recording_rejected(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
        corrupt_audio_sample: bytes,
    ) -> None:
        """Requirement: Reject invalid and corrupted audio files."""
        # Replace middle recording with corrupted bytes
        samples = [valid_enrollment_audio_samples[0], corrupt_audio_sample, valid_enrollment_audio_samples[2]]
        with pytest.raises(EnrollmentValidationError) as exc_info:
            enrollment_service.enroll(
                user_id="alice_test",
                audio_sources=samples,
                consent=True,
            )
        assert "recording 2 failed preprocessing" in str(exc_info.value).lower()

    def test_silent_audio_recording_rejected(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
        silent_audio_sample: bytes,
    ) -> None:
        """Requirement: Reject silent recordings."""
        samples = [valid_enrollment_audio_samples[0], silent_audio_sample, valid_enrollment_audio_samples[2]]
        with pytest.raises(EnrollmentValidationError) as exc_info:
            enrollment_service.enroll(
                user_id="alice_test",
                audio_sources=samples,
                consent=True,
            )
        assert "recording 2 failed preprocessing" in str(exc_info.value).lower()

    def test_empty_audio_bytes_rejected(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Detect empty recordings."""
        samples = [valid_enrollment_audio_samples[0], b"", valid_enrollment_audio_samples[2]]
        with pytest.raises(EnrollmentValidationError) as exc_info:
            enrollment_service.enroll(
                user_id="alice_test",
                audio_sources=samples,
                consent=True,
            )
        assert "recording 2 failed preprocessing" in str(exc_info.value).lower()

    def test_invalid_user_id_rejected(
        self,
        enrollment_service: EnrollmentService,
        valid_enrollment_audio_samples: List[bytes],
    ) -> None:
        """Requirement: Sanitize and validate user ID."""
        with pytest.raises(EnrollmentValidationError):
            enrollment_service.enroll(user_id="", audio_sources=valid_enrollment_audio_samples, consent=True)

        with pytest.raises(EnrollmentValidationError):
            enrollment_service.enroll(user_id="   ", audio_sources=valid_enrollment_audio_samples, consent=True)

    def test_config_validation_bounds(self) -> None:
        """Verify min_recordings cannot exceed max_recordings."""
        with pytest.raises(ValueError):
            EnrollmentConfig(min_recordings=10, max_recordings=5)

