"""SentinelAI Voice Verification Platform - FastAPI Application Entry Point.

Initializes the FastAPI application, mounts core API routers including
authentication, user management, biometric consent, audio preprocessing,
voice enrollment, speaker verification, and operational health monitoring modules.
Configures request correlation tracing, structured logging, rate limiting, and security invariants.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from sentinelai.audio.api import router as audio_router
from sentinelai.auth.api import router as auth_router
from sentinelai.auth.exceptions import (
    AccountInactiveError,
    AccountTemporarilyThrottledError,
    AuthError,
    CSRFValidationError,
    EmailAlreadyExistsError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
    InvalidTokenError,
    LastAdminError,
    RateLimitExceededError,
    SelfModificationError,
    TokenExpiredError,
    TokenReusedError,
    UserNotFoundError,
    WeakPasswordError,
)
from sentinelai.biometrics.api import router as biometrics_router
from sentinelai.config import get_settings
from sentinelai.consent.api import router as consent_router
from sentinelai.database.connection import close_db
from sentinelai.enrollment.api import router as enrollment_router
from sentinelai.monitoring.api import router as health_router
from sentinelai.monitoring.logging import StructuredLoggingMiddleware, setup_logging
from sentinelai.monitoring.request_tracing import RequestTracingMiddleware
from sentinelai.security.config_validator import validate_runtime_configuration
from sentinelai.security.rate_limiter import get_rate_limiter_backend
from sentinelai.users.api import admin_router, user_router
from sentinelai.verification.api import router as verification_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the SentinelAI Voice Verification FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # Application startup
        setup_logging(settings)
        validate_runtime_configuration(settings)
        get_rate_limiter_backend(settings)
        yield
        # Application shutdown
        await close_db()

    docs_url = "/docs" if settings.expose_docs else None
    redoc_url = "/redoc" if settings.expose_docs else None
    openapi_url = "/openapi.json" if settings.expose_docs else None

    application = FastAPI(
        title="SentinelAI Voice Verification Platform",
        description="Autonomous AI Voice Verification, Speaker Defense, Authentication, and Biometric API.",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # Middleware registration: Starlette executes middleware in reverse order of addition
    # 1. Inner: Cross-Origin Resource Sharing (CORS)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Middle: Structured Access Logging (records route, latency, and status)
    application.add_middleware(StructuredLoggingMiddleware)

    # 3. Outermost: Request Correlation ID Tracing (binds X-Request-ID to context)
    application.add_middleware(RequestTracingMiddleware)

    # Root informational endpoint
    @application.get("/", tags=["Health"])
    async def root():
        """Service status and platform identity."""
        return {
            "status": "online",
            "service": "SentinelAI Voice Verification Platform",
            "version": "0.1.0",
            "docs": "/docs" if settings.expose_docs else None,
        }

    # Exception handler for domain AuthErrors (includes RateLimit & Throttling)
    @application.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError):
        headers = {}
        if hasattr(exc, "retry_after"):
            headers["Retry-After"] = str(getattr(exc, "retry_after"))

        if hasattr(exc, "status_code"):
            status_code = getattr(exc, "status_code")
        elif isinstance(exc, (InvalidCredentialsError, InvalidTokenError, TokenExpiredError, TokenReusedError)):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, (InsufficientPermissionsError, AccountInactiveError, CSRFValidationError)):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, UserNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, EmailAlreadyExistsError):
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_400_BAD_REQUEST

        content = {
            "success": False,
            "message": exc.message,
            "error_code": exc.error_code,
            "detail": exc.message,
        }
        if hasattr(exc, "retry_after"):
            content["retry_after"] = getattr(exc, "retry_after")

        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=headers,
        )

    # Exception handler for database errors: prevents leakage of SQL syntax or credentials
    @application.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.error("Internal database exception trapped: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": "An internal database error occurred. Please try again later.",
                "error_code": "DATABASE_ERROR",
                "detail": "An internal database error occurred.",
            },
        )

    # Register modular API routers
    # Operational Health & Monitoring (Phase 7E)
    application.include_router(health_router)

    # Authentication & User Management (Phase 7C)
    application.include_router(auth_router)
    application.include_router(user_router)
    application.include_router(admin_router)
    application.include_router(consent_router)

    # Live Biometric Pipeline Bridge (Phase 7D)
    application.include_router(biometrics_router)

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
