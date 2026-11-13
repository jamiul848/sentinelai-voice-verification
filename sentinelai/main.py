"""SentinelAI Voice Verification Platform - FastAPI Application Entry Point.

Initializes the FastAPI application, mounts core API routers including
authentication, user management, biometric consent, audio preprocessing,
voice enrollment, and speaker verification modules.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sentinelai.audio.api import router as audio_router
from sentinelai.auth.api import router as auth_router
from sentinelai.auth.exceptions import (
    AccountInactiveError,
    AuthError,
    CSRFValidationError,
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    LastAdminError,
    SelfModificationError,
    TokenExpiredError,
    TokenReusedError,
    UserNotFoundError,
    WeakPasswordError,
)
from sentinelai.config import get_settings
from sentinelai.consent.api import router as consent_router
from sentinelai.enrollment.api import router as enrollment_router
from sentinelai.users.api import admin_router, user_router
from sentinelai.verification.api import router as verification_router


def create_app() -> FastAPI:
    """Create and configure the SentinelAI Voice Verification FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    application = FastAPI(
        title="SentinelAI Voice Verification Platform",
        description="Autonomous AI Voice Verification, Speaker Defense, Authentication, and Biometric API.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check and root informational endpoints
    @application.get("/", tags=["Health"])
    async def root():
        """Service status and platform identity."""
        return {
            "status": "online",
            "service": "SentinelAI Voice Verification Platform",
            "version": "0.1.0",
            "docs": "/docs",
        }

    @application.get("/health", tags=["Health"])
    async def health_check():
        """Liveness health check endpoint."""
        return {"status": "healthy"}

    # Custom exception handler for domain AuthErrors
    @application.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError):
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(exc, (InvalidCredentialsError, InvalidTokenError, TokenExpiredError, TokenReusedError)):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, (InsufficientPermissionsError, AccountInactiveError, CSRFValidationError)):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, UserNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, EmailAlreadyExistsError):
            status_code = status.HTTP_409_CONFLICT

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "message": exc.message,
                "error_code": exc.error_code,
                "detail": exc.message,
            },
        )

    # Register modular API routers
    # Authentication & User Management (Phase 7C)
    application.include_router(auth_router)
    application.include_router(user_router)
    application.include_router(admin_router)
    application.include_router(consent_router)

    # Audio Preprocessing, Enrollment & Verification Engine (Phases 1-4)
    application.include_router(audio_router)
    application.include_router(enrollment_router)
    application.include_router(verification_router)

    return application


# Top-level ASGI application instance for Uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("sentinelai.main:app", host="127.0.0.1", port=8000, reload=True)
