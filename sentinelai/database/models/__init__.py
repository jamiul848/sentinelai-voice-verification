"""Sentinel Voice - Database Models Package.

Exports the ten core database entities:
1. User
2. Role
3. UserRole
4. RefreshToken
5. ApiCredential
6. ConsentRecord
7. VoiceProfile
8. EnrollmentRecord
9. VerificationEvent
10. AuditLog
"""

from sentinelai.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from sentinelai.database.models.api_credential import ApiCredential
from sentinelai.database.models.audit_log import AuditLog
from sentinelai.database.models.consent_record import ConsentRecord
from sentinelai.database.models.enrollment_record import EnrollmentRecord
from sentinelai.database.models.refresh_token import RefreshToken
from sentinelai.database.models.role import Role
from sentinelai.database.models.threshold_configuration import ThresholdConfiguration
from sentinelai.database.models.user import User
from sentinelai.database.models.user_role import UserRole
from sentinelai.database.models.verification_event import VerificationEvent
from sentinelai.database.models.voice_profile import VoiceProfile

__all__ = [
    "Base",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "User",
    "Role",
    "UserRole",
    "RefreshToken",
    "ApiCredential",
    "ConsentRecord",
    "VoiceProfile",
    "EnrollmentRecord",
    "VerificationEvent",
    "AuditLog",
    "ThresholdConfiguration",
]

