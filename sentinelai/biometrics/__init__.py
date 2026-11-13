"""Sentinel Voice - Biometric Subsystem Package.

Integrates the ECAPA-TDNN speaker recognition engine with PostgreSQL 18 persistence,
AES-256-GCM envelope encryption, legal consent verification, and FastAPI REST endpoints.
"""

from sentinelai.biometrics.api import router as biometrics_router
from sentinelai.biometrics.enrollment_service import BiometricEnrollmentService
from sentinelai.biometrics.exceptions import (
    ActiveProfileAlreadyExistsError,
    BiometricConsentRequiredError,
    BiometricError,
    BiometricStorageError,
    DirectoryTraversalError,
    InsufficientEnrollmentSamplesError,
    InvalidEnrollmentAudioError,
    ProfileNotFoundError,
    ProfileRevokedError,
    ThresholdConfigurationError,
    VectorTamperedError,
)
from sentinelai.biometrics.profile_service import BiometricProfileService
from sentinelai.biometrics.schemas import (
    EnrollmentResponse,
    EnrollmentSampleMetadata,
    ProfileRevocationResponse,
    ReEnrollmentResponse,
    VerificationHistoryItem,
    VerificationHistoryResponse,
    VerificationResponse,
    VoiceProfileDetailResponse,
    VoiceProfileResponse,
)
from sentinelai.biometrics.storage import BiometricStorageManager
from sentinelai.biometrics.verification_service import BiometricVerificationService

__all__ = [
    "biometrics_router",
    "BiometricEnrollmentService",
    "BiometricVerificationService",
    "BiometricProfileService",
    "BiometricStorageManager",
    "BiometricError",
    "BiometricConsentRequiredError",
    "ActiveProfileAlreadyExistsError",
    "ProfileNotFoundError",
    "ProfileRevokedError",
    "InsufficientEnrollmentSamplesError",
    "InvalidEnrollmentAudioError",
    "ThresholdConfigurationError",
    "VectorTamperedError",
    "BiometricStorageError",
    "DirectoryTraversalError",
    "EnrollmentResponse",
    "EnrollmentSampleMetadata",
    "VerificationResponse",
    "VoiceProfileResponse",
    "VoiceProfileDetailResponse",
    "VerificationHistoryItem",
    "VerificationHistoryResponse",
    "ReEnrollmentResponse",
    "ProfileRevocationResponse",
]

