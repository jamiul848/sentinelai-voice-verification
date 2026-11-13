"""Sentinel Voice - Operational Health API Router.

Exposes liveness, readiness, and administrator-restricted detailed diagnostic probes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.auth.dependencies import require_role
from sentinelai.database.connection import get_db_session
from sentinelai.database.models.user import User
from sentinelai.monitoring.health import HealthChecker

router = APIRouter(tags=["Health & Monitoring"])
health_checker = HealthChecker()


@router.get(
    "/health",
    summary="Application Health",
    description="Standard basic health check verifying process responsiveness.",
)
async def basic_health():
    """Basic health endpoint returning service status."""
    return {"status": "healthy"}


@router.get(
    "/health/live",
    summary="Kubernetes Liveness Probe",
    description="Instantaneous liveness verification. Always returns 200 while process event loop is alive.",
)
async def liveness_probe():
    """Liveness probe without external I/O."""
    return health_checker.get_liveness()


@router.get(
    "/health/ready",
    summary="Kubernetes Readiness Probe",
    description="Verifies essential database connectivity before routing production traffic.",
)
async def readiness_probe(session: AsyncSession = Depends(get_db_session)):
    """Readiness probe evaluating PostgreSQL and cache availability."""
    is_ready, data = await health_checker.get_readiness(session)
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=data)


@router.get(
    "/health/detailed",
    summary="Detailed Operational Diagnostics",
    description="Administrative operational inspection of DB latency, model cache, storage, and uptime. Restricted to administrators.",
)
async def detailed_health(
    current_admin: User = Depends(require_role("ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db_session),
):
    """Detailed health assessment restricted to administrators."""
    is_ready, data = await health_checker.get_detailed_health(session)
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=data)
