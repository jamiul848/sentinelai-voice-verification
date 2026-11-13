"""Sentinel Voice - Authentication, User & Consent Pydantic Schemas.

Defines API input models, sanitized output projections, and standardized API response envelopes.
INVARIANT: Never expose password hashes, refresh token hashes, or raw biometric paths/vectors.
"""

from datetime import datetime
import re
from typing import Any, Generic, List, Optional, TypeVar
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from sentinelai.auth.exceptions import PasswordMismatchError, WeakPasswordError
from sentinelai.auth.password import validate_password_strength

T = TypeVar("T")


# ------------------------------------------------------------------------------
# Standard API Response Envelope
# ------------------------------------------------------------------------------
class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Human-readable status summary")
    data: Optional[T] = Field(default=None, description="Response payload")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code")


# ------------------------------------------------------------------------------
# Authentication Schemas
# ------------------------------------------------------------------------------
class UserRegistrationRequest(BaseModel):
    """User account registration payload."""

    full_name: str = Field(..., min_length=2, max_length=150, description="Full name")
    email: str = Field(..., max_length=255, description="Unique email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")
    password_confirm: str = Field(..., min_length=8, max_length=128, description="Password confirmation")
    accept_privacy_terms: bool = Field(
        ...,
        description="Explicit acceptance of privacy policy and terms of service",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError(f"Invalid email address format: '{v}'")
        return v

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        validate_password_strength(v)
        return v

    @model_validator(mode="after")
    def verify_password_match(self) -> "UserRegistrationRequest":
        if self.password != self.password_confirm:
            raise PasswordMismatchError("Password and confirmation password do not match.")
        if not self.accept_privacy_terms:
            raise ValueError("You must accept the privacy terms to register.")
        return self


class UserLoginRequest(BaseModel):
    """User login credential payload."""

    email: str = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Sanitized public user representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique user UUID")
    email: str = Field(..., description="Email address")
    full_name: str = Field(..., description="Full display name")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verification status")
    roles: List[str] = Field(default_factory=list, description="Assigned RBAC role names")
    created_at: datetime = Field(..., description="Account creation timestamp")


class TokenResponse(BaseModel):
    """JWT Access and Refresh token response."""

    access_token: str = Field(..., description="Short-lived JWT access token")
    refresh_token: str = Field(..., description="Opaque secure refresh token")
    token_type: str = Field(default="bearer", description="Token type indicator")
    expires_in: int = Field(..., description="Access token expiration window in seconds")
    csrf_token: Optional[str] = Field(default=None, description="Double-submit CSRF token")
    user: UserResponse = Field(..., description="Authenticated user profile")


class RefreshTokenRequest(BaseModel):
    """Token refresh request payload."""

    refresh_token: Optional[str] = Field(
        default=None,
        description="Opaque refresh token (if not supplied via HttpOnly cookie)",
    )


# ------------------------------------------------------------------------------
# User Management Schemas
# ------------------------------------------------------------------------------
class UpdateProfileRequest(BaseModel):
    """User self-service profile update payload."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=150, description="Updated full name")


class ChangePasswordRequest(BaseModel):
    """User password change payload."""

    current_password: str = Field(..., description="Current plaintext password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    new_password_confirm: str = Field(..., min_length=8, max_length=128, description="Confirm new password")

    @field_validator("new_password")
    @classmethod
    def check_new_password_complexity(cls, v: str) -> str:
        validate_password_strength(v)
        return v

    @model_validator(mode="after")
    def verify_password_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.new_password_confirm:
            raise PasswordMismatchError("New password and confirmation do not match.")
        return self


# ------------------------------------------------------------------------------
# Administrator Management Schemas
# ------------------------------------------------------------------------------
class AdminUpdateStatusRequest(BaseModel):
    """Administrator user status modification payload."""

    is_active: bool = Field(..., description="New account active status")


class AdminUpdateRolesRequest(BaseModel):
    """Administrator user role assignment payload."""

    roles: List[str] = Field(..., min_length=1, description="List of role names to assign (e.g. ['USER', 'ADMIN'])")

    @field_validator("roles")
    @classmethod
    def uppercase_roles(cls, v: List[str]) -> List[str]:
        return [r.strip().upper() for r in v if r.strip()]


# ------------------------------------------------------------------------------
# Biometric Consent Schemas
# ------------------------------------------------------------------------------
class GrantConsentRequest(BaseModel):
    """Explicit biometric legal consent grant payload."""

    consent_version: str = Field(default="1.0", max_length=20, description="Legal consent policy version")
    consent_type: str = Field(
        default="VOICE_BIOMETRIC_ENROLLMENT",
        max_length=50,
        description="Scope/purpose of biometric processing",
    )


class RevokeConsentRequest(BaseModel):
    """Explicit biometric legal consent revocation payload."""

    consent_type: str = Field(
        default="VOICE_BIOMETRIC_ENROLLMENT",
        max_length=50,
        description="Scope of biometric consent being revoked",
    )
    reason: Optional[str] = Field(default=None, max_length=255, description="Optional revocation reason")


class ConsentResponse(BaseModel):
    """Sanitized legal consent audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Consent record ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    consent_type: str = Field(..., description="Scope/purpose of processing")
    consent_granted: bool = Field(..., description="Whether consent was granted or revoked")
    consent_version: str = Field(..., description="Policy version")
    created_at: datetime = Field(..., description="Timestamp of consent decision")

