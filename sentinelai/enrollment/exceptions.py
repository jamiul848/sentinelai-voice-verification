"""SentinelAI Enrollment Exceptions.

Domain-specific exceptions for speaker voice enrollment, profile management,
and embedding aggregation.
"""

from typing import Optional


class EnrollmentError(Exception):
    """Base exception for all voice enrollment operations."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class EnrollmentConsentError(EnrollmentError):
    """Raised when user consent is missing or rejected."""
    pass


class InsufficientRecordingsError(EnrollmentError):
    """Raised when the number of valid recordings is below the required threshold."""

    def __init__(self, message: str, count: int, min_required: int, details: Optional[dict] = None) -> None:
        extra = {"count": count, "min_required": min_required}
        if details:
            extra.update(details)
        super().__init__(message, details=extra)
        self.count = count
        self.min_required = min_required


class ExcessiveRecordingsError(EnrollmentError):
    """Raised when the number of recordings exceeds the configured maximum."""

    def __init__(self, message: str, count: int, max_allowed: int, details: Optional[dict] = None) -> None:
        extra = {"count": count, "max_allowed": max_allowed}
        if details:
            extra.update(details)
        super().__init__(message, details=extra)
        self.count = count
        self.max_allowed = max_allowed


class EnrollmentValidationError(EnrollmentError):
    """Raised when audio inputs fail acoustic or structural validation checks."""
    pass


class DuplicateEnrollmentError(EnrollmentError):
    """Raised when enrolling a user that already possesses an active profile."""
    pass


class ProfileNotFoundError(EnrollmentError):
    """Raised when a requested speaker profile cannot be located."""
    pass


class ProfileRevokedError(EnrollmentError):
    """Raised when an operation attempts to access or verify a revoked profile."""
    pass


class AggregationError(EnrollmentError):
    """Raised when embedding aggregation fails due to dimension mismatch or numerical issues."""
    pass


class StorageError(EnrollmentError):
    """Raised when storage read, write, or permission operations fail."""
    pass

