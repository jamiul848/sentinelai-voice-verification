"""Sentinel Voice - Biometric Subsystem Domain Exceptions.

Provides granular, standardized exceptions for voice enrollment, probe verification,
profile lifecycle states, dynamic thresholding, envelope cryptographic storage,
and directory traversal defenses.
"""

from typing import Optional

from sentinelai.auth.exceptions import AuthError


class BiometricError(AuthError):
    """Base exception for all biometric pipeline and profile operations."""

    def __init__(
        self,
        message: str = "Biometric processing error",
        error_code: str = "BIOMETRIC_ERROR",
        status_code: int = 400,
    ) -> None:
        super().__init__(message=message, error_code=error_code)
        self.status_code = status_code


class BiometricConsentRequiredError(BiometricError):
    """Raised when an operation requires explicit active biometric consent."""

    def __init__(
        self,
        message: str = "Biometric processing requires explicit user consent (GDPR / BIPA).",
    ) -> None:
        super().__init__(
            message=message,
            error_code="BIOMETRIC_CONSENT_REQUIRED",
            status_code=403,
        )


class ActiveProfileAlreadyExistsError(BiometricError):
    """Raised when enrolling a voiceprint while an active profile is already registered."""

    def __init__(
        self,
        message: str = "An active voice profile already exists for this account. Use re-enrollment to update.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="ACTIVE_PROFILE_ALREADY_EXISTS",
            status_code=409,
        )


class ProfileNotFoundError(BiometricError):
    """Raised when an active voice profile is expected but does not exist."""

    def __init__(
        self,
        message: str = "No active voice profile found for this user. Enrollment required.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="PROFILE_NOT_FOUND",
            status_code=404,
        )


class ProfileRevokedError(BiometricError):
    """Raised when attempting verification against a revoked voice profile."""

    def __init__(
        self,
        message: str = "Voice profile is revoked and cannot be used for speaker verification.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="PROFILE_REVOKED",
            status_code=400,
        )


class InsufficientEnrollmentSamplesError(BiometricError):
    """Raised when enrollment receives fewer than the minimum required audio recordings."""

    def __init__(
        self,
        message: str = "Voice enrollment requires at least 3 valid audio recordings.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_ENROLLMENT_SAMPLES",
            status_code=400,
        )


class InvalidEnrollmentAudioError(BiometricError):
    """Raised when enrollment or verification audio fails acoustic quality validation."""

    def __init__(
        self,
        message: str = "Audio sample is invalid, corrupt, or does not meet quality requirements.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="INVALID_AUDIO_SAMPLE",
            status_code=400,
        )


class ThresholdConfigurationError(BiometricError):
    """Raised when no calibrated verification threshold exists for the active model."""

    def __init__(
        self,
        message: str = "Calibrated decision threshold is not configured for the active neural backbone.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="THRESHOLD_CONFIG_ERROR",
            status_code=500,
        )


class VectorTamperedError(BiometricError):
    """Raised when an encrypted biometric vector fails authentication tag or checksum validation."""

    def __init__(
        self,
        message: str = "Biometric vector payload integrity check failed: data tampered or corrupted.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="VECTOR_TAMPERED",
            status_code=500,
        )


class BiometricStorageError(BiometricError):
    """Raised when writing, reading, or securely shredding biometric containers fails."""

    def __init__(
        self,
        message: str = "Biometric storage operation failed.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="BIOMETRIC_STORAGE_ERROR",
            status_code=500,
        )


class DirectoryTraversalError(BiometricError):
    """Raised when a storage path parameter attempts to traverse outside the authorized store root."""

    def __init__(
        self,
        message: str = "Access denied: illegal storage directory traversal detected.",
    ) -> None:
        super().__init__(
            message=message,
            error_code="DIRECTORY_TRAVERSAL_DETECTED",
            status_code=403,
        )

