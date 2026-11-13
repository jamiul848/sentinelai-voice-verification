"""Sentinel Voice - Operational Health Check Service.

Implements cloud-native, Kubernetes-compatible operational health probes:
1. Liveness (/health/live): Verifies the FastAPI event loop is responsive without external I/O.
2. Readiness (/health/ready): Verifies PostgreSQL database connectivity (and Redis if configured).
3. Detailed Health (/health/detailed): Restricted administrator diagnosis inspecting uptime,
   DB latency, model cache state (without instantiating weights), storage, and crypto config.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import Any, Dict, Tuple

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from sentinelai.config import Settings, get_settings
from sentinelai.database.connection import get_async_engine
from sentinelai.speaker.model import get_model_loader

# Process startup timestamp
PROCESS_START_TIME = time.time()


class HealthChecker:
    """Provides operational health assessment routines."""

    def __init__(self, settings: Settings = None) -> None:
        self.settings = settings or get_settings()

    def get_liveness(self) -> Dict[str, Any]:
        """Perform instantaneous liveness evaluation."""
        return {
            "status": "healthy",
            "service": self.settings.app_name,
            "version": self.settings.app_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_readiness(self, session: AsyncSession) -> Tuple[bool, Dict[str, Any]]:
        """Verify essential dependencies to determine if process can accept production traffic."""
        is_ready = True
        components: Dict[str, Any] = {}

        # 1. Check PostgreSQL Database Connectivity
        try:
            start = time.perf_counter()
            await session.execute(text("SELECT 1"))
            db_latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            components["database"] = {
                "status": "connected",
                "latency_ms": db_latency_ms,
            }
        except Exception as err:
            is_ready = False
            components["database"] = {
                "status": "disconnected",
                "error": type(err).__name__,
            }

        # 2. Check Redis (if explicitly configured)
        if self.settings.redis_url and self.settings.rate_limit_storage in ("redis", "auto"):
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url(self.settings.redis_url, socket_connect_timeout=2.0)
                await client.ping()
                await client.aclose()
                components["redis"] = {"status": "connected"}
            except Exception as err:
                # If rate_limit_storage is strictly redis, readiness fails
                if self.settings.rate_limit_storage == "redis":
                    is_ready = False
                components["redis"] = {
                    "status": "unavailable",
                    "error": type(err).__name__,
                }
        else:
            components["redis"] = {"status": "disabled", "mode": "in-memory"}

        overall_status = "ready" if is_ready else "unready"
        return is_ready, {
            "status": overall_status,
            "service": self.settings.app_name,
            "version": self.settings.app_version,
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def get_detailed_health(self, session: AsyncSession) -> Tuple[bool, Dict[str, Any]]:
        """Construct detailed diagnostic ledger for authorized administrators.

        INVARIANT: Inspects model state via `loader.is_loaded` WITHOUT calling `load()`
        to prevent unintended cold-start latency or memory spikes.
        """
        is_ready, readiness_data = await self.get_readiness(session)
        uptime_seconds = round(time.time() - PROCESS_START_TIME, 1)

        # 1. ECAPA-TDNN Model Status (Non-loading inspection)
        loader = get_model_loader()
        model_info = {
            "is_loaded": loader.is_loaded,
            "model_identifier": self.settings.model_identifier,
            "device": str(loader.get_device()),
            "embedding_dimension": self.settings.embedding_dimension,
        }

        # 2. Biometric Storage Directory Accessibility
        store_path = Path(self.settings.biometric_store_path).resolve()
        storage_accessible = store_path.exists() and os.access(store_path, os.W_OK)
        storage_info = {
            "accessible": storage_accessible,
            "storage_root": str(store_path.name),  # Basename only, avoiding internal path leaks
        }

        # 3. Cryptographic Key Configuration Status (Never leaks key bytes!)
        has_encryption_key = bool(self.settings.biometric_encryption_key.strip())
        encryption_info = {
            "configured": has_encryption_key,
            "algorithm": "AES-256-GCM-Envelope-V2",
        }

        detailed = {
            **readiness_data,
            "environment": self.settings.environment,
            "uptime_seconds": uptime_seconds,
            "ecapa_engine": model_info,
            "biometric_storage": storage_info,
            "encryption_service": encryption_info,
        }

        return is_ready, detailed

