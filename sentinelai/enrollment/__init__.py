"""SentinelAI Voice Enrollment Module.

Exports enrollment service, configuration, schemas, storage, and aggregation utilities.
"""

from sentinelai.enrollment.aggregation import AggregationResult, aggregate_embeddings
from sentinelai.enrollment.api import router as enrollment_router
from sentinelai.enrollment.config import EnrollmentConfig
from sentinelai.enrollment.exceptions import (
    AggregationError,
    DuplicateEnrollmentError,
    EnrollmentConsentError,
    EnrollmentError,
    EnrollmentValidationError,
    ExcessiveRecordingsError,
    InsufficientRecordingsError,
    ProfileNotFoundError,
    ProfileRevokedError,
    StorageError,
)
from sentinelai.enrollment.schemas import (
    EnrollmentResponse,
    EnrollmentStatusResponse,
    ProfileStatus,
    ReEnrollmentResponse,
    RevocationResponse,
    SpeakerProfile,
    SpeakerProfilePublic,
    UserEnrollmentStatus,
)
from sentinelai.enrollment.service import EnrollmentService
from sentinelai.enrollment.storage import LocalFileProfileStorage, ProfileStorageBackend

__all__ = [
    "EnrollmentConfig",
    "EnrollmentService",
    "enrollment_router",
    "ProfileStorageBackend",
    "LocalFileProfileStorage",
    "SpeakerProfile",
    "SpeakerProfilePublic",
    "ProfileStatus",
    "UserEnrollmentStatus",
    "EnrollmentResponse",
    "ReEnrollmentResponse",
    "RevocationResponse",
    "EnrollmentStatusResponse",
    "aggregate_embeddings",
    "AggregationResult",
    "EnrollmentError",
    "EnrollmentConsentError",
    "InsufficientRecordingsError",
    "ExcessiveRecordingsError",
    "EnrollmentValidationError",
    "DuplicateEnrollmentError",
    "ProfileNotFoundError",
    "ProfileRevokedError",
    "AggregationError",
    "StorageError",
]

