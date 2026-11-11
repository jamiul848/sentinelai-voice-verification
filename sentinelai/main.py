"""SentinelAI Voice Verification Platform - FastAPI Application Entry Point.

Initializes the FastAPI application and mounts core API routers including
the audio preprocessing module.
"""

from fastapi import FastAPI
from sentinelai.audio.api import router as audio_router
from sentinelai.enrollment.api import router as enrollment_router


def create_app() -> FastAPI:
    """Create and configure the SentinelAI Voice Verification FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    application = FastAPI(
        title="SentinelAI Voice Verification Platform",
        description="Autonomous AI Voice Verification, Speaker Defense, and Audio Preprocessing API.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
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

    # Register modular API routers
    # audio_router has prefix="/audio", resulting in endpoints like /audio/preprocess
    application.include_router(audio_router)
    # enrollment_router has prefix="/enrollment", resulting in endpoints like /enrollment/register
    application.include_router(enrollment_router)

    return application


# Top-level ASGI application instance for Uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("sentinelai.main:app", host="127.0.0.1", port=8000, reload=True)

