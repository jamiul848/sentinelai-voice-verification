"""Domain exceptions for the SentinelAI Speaker Verification module."""

from typing import Optional


class VerificationError(Exception):
    """Base exception for all speaker verification errors."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class ProfileNotFoundError(VerificationError):
    """Raised when an enrolled speaker profile cannot be found."""

    pass


class ProfileRevokedError(VerificationError):
    """Raised when attempting to verify against a revoked speaker profile."""

    pass


class InvalidAudioInputError(VerificationError):
    """Raised when the submitted verification audio fails validation."""

    pass


class ThresholdValidationError(VerificationError):
    """Raised when a verification threshold is invalid or out of range."""

    pass


class VerificationScoringError(VerificationError):
    """Raised when similarity score calculation fails due to numerical or dimension issues."""

    pass


class AuditLoggingError(VerificationError):
    """Raised when an audit event fails to be recorded."""

    pass


class UnauthorizedVerificationError(VerificationError):
    """Raised when a verification request fails authorization checks."""

    pass
