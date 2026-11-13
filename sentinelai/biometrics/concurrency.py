"""Sentinel Voice - Biometric Inference Concurrency & Resource Guard.

Protects system resources against CPU and memory exhaustion:
1. Implements bounded concurrency using an asyncio.Semaphore.
2. Prevents high concurrent traffic from starving other request threads.
3. Facilitates offloading CPU-heavy tensor inference to Python thread pool workers.
"""

import asyncio
from typing import Optional

from sentinelai.config import get_settings

_inference_semaphore: Optional[asyncio.Semaphore] = None


def get_inference_semaphore() -> asyncio.Semaphore:
    """Retrieve or initialize the bounded concurrency semaphore for ECAPA inference."""
    global _inference_semaphore
    if _inference_semaphore is None:
        settings = get_settings()
        _inference_semaphore = asyncio.Semaphore(settings.max_concurrent_inferences)
    return _inference_semaphore


def reset_inference_semaphore(limit: Optional[int] = None) -> asyncio.Semaphore:
    """Reset or reconfigure the inference semaphore (useful for test fixtures)."""
    global _inference_semaphore
    settings = get_settings()
    concurrency = limit if limit is not None else settings.max_concurrent_inferences
    _inference_semaphore = asyncio.Semaphore(concurrency)
    return _inference_semaphore

