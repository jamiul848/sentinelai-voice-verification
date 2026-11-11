"""SentinelAI Speaker Verification Module.

Exports the 1:1 speaker verification service, decision thresholding engine,
scoring utilities, schemas, audit loggers, and domain exceptions.
"""

from sentinelai.verification.audit import (
    AuditLoggerBackend,
    AuditRecord,
    InMemoryAuditLogger,
    JsonLinesAuditLogger,
)
from sentinelai.verification.config import VerificationConfig
from sentinelai.verification.exceptions import (
    AuditLoggingError,
    InvalidAudioInputError,
    ProfileNotFoundError,
    ProfileRevokedError,
    ThresholdValidationError,
    UnauthorizedVerificationError,
    VerificationError,
    VerificationScoringError,
)
from sentinelai.verification.schemas import (
    VerificationHealthResponse,
    VerificationResponse,
    VerificationStatus,
)
from sentinelai.verification.scoring import compute_verification_score
from sentinelai.verification.service import SpeakerVerificationService
from sentinelai.verification.threshold import VerificationThreshold

__all__ = [
    "VerificationConfig",
    "VerificationThreshold",
    "compute_verification_score",
    "SpeakerVerificationService",
    "VerificationResponse",
    "VerificationStatus",
    "VerificationHealthResponse",
    "AuditRecord",
    "AuditLoggerBackend",
    "JsonLinesAuditLogger",
    "InMemoryAuditLogger",
    "VerificationError",
    "ProfileNotFoundError",
    "ProfileRevokedError",
    "InvalidAudioInputError",
    "ThresholdValidationError",
    "VerificationScoringError",
    "AuditLoggingError",
    "UnauthorizedVerificationError",
]

