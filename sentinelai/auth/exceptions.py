"""Sentinel Voice - Authentication & Authorization Exceptions."""


class AuthError(Exception):
    """Base exception for authentication and authorization errors."""

    def __init__(self, message: str, error_code: str = "AUTH_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class InvalidCredentialsError(AuthError):
    """Raised when email/password verification fails or user is not found."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message, error_code="INVALID_CREDENTIALS")


class AccountInactiveError(AuthError):
    """Raised when an account is deactivated or suspended."""

    def __init__(self, message: str = "Account is inactive or suspended") -> None:
        super().__init__(message, error_code="ACCOUNT_INACTIVE")


class EmailAlreadyExistsError(AuthError):
    """Raised when registering an email that already exists."""

    def __init__(self, message: str = "Email address is already registered") -> None:
        super().__init__(message, error_code="EMAIL_ALREADY_EXISTS")


class WeakPasswordError(AuthError):
    """Raised when a password fails complexity requirements."""

    def __init__(
        self,
        message: str = (
            "Password must be at least 8 characters long and contain at least "
            "one uppercase letter, one lowercase letter, one digit, and one special character."
        ),
    ) -> None:
        super().__init__(message, error_code="WEAK_PASSWORD")


class PasswordMismatchError(AuthError):
    """Raised when password and password confirmation do not match."""

    def __init__(self, message: str = "Passwords do not match") -> None:
        super().__init__(message, error_code="PASSWORD_MISMATCH")


class InvalidTokenError(AuthError):
    """Raised when a JWT or refresh token is malformed, has invalid signature, or wrong type."""

    def __init__(self, message: str = "Invalid or malformed authentication token") -> None:
        super().__init__(message, error_code="INVALID_TOKEN")


class TokenExpiredError(AuthError):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Authentication token has expired") -> None:
        super().__init__(message, error_code="TOKEN_EXPIRED")


class TokenReusedError(AuthError):
    """Raised when a previously revoked refresh token is presented (token theft detection)."""

    def __init__(
        self,
        message: str = "Refresh token reuse detected. All active sessions have been revoked for security.",
    ) -> None:
        super().__init__(message, error_code="TOKEN_REUSE_DETECTED")


class InsufficientPermissionsError(AuthError):
    """Raised when a user lacks the required RBAC role or permission."""

    def __init__(self, message: str = "Insufficient permissions to perform this action") -> None:
        super().__init__(message, error_code="INSUFFICIENT_PERMISSIONS")


class CSRFValidationError(AuthError):
    """Raised when CSRF token is missing or does not match cookie."""

    def __init__(self, message: str = "CSRF verification failed") -> None:
        super().__init__(message, error_code="CSRF_VERIFICATION_FAILED")


class UserNotFoundError(AuthError):
    """Raised when a requested user entity is not found."""

    def __init__(self, message: str = "User not found") -> None:
        super().__init__(message, error_code="USER_NOT_FOUND")


class SelfModificationError(AuthError):
    """Raised when an administrator attempts to perform an invalid self-action."""

    def __init__(self, message: str = "Administrators cannot perform this action on themselves") -> None:
        super().__init__(message, error_code="SELF_MODIFICATION_FORBIDDEN")


class LastAdminError(AuthError):
    """Raised when attempting to deactivate, demote, or delete the last active administrator."""

    def __init__(
        self,
        message: str = "Cannot deactivate, demote, or delete the last active administrator",
    ) -> None:
        super().__init__(message, error_code="LAST_ADMIN_PROTECTED")


class ConsentRequiredError(AuthError):
    """Raised when an operation requires active biometric consent that is absent or revoked."""

    def __init__(
        self,
        message: str = "Biometric processing requires explicit, active user consent",
    ) -> None:
        super().__init__(message, error_code="CONSENT_REQUIRED")

