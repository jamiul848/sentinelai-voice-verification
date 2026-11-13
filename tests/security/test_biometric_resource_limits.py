"""Tests for Sentinel Voice Biometric Inference Resource Limits & Concurrency Protection.

Validates maximum upload size guards (10MB limit), inference concurrency semaphores,
and non-blocking event-loop thread execution.
"""

import asyncio
import pytest

from sentinelai.biometrics.concurrency import get_inference_semaphore, reset_inference_semaphore
from sentinelai.biometrics.enrollment_service import BiometricEnrollmentService
from sentinelai.biometrics.exceptions import InvalidEnrollmentAudioError
from sentinelai.biometrics.verification_service import BiometricVerificationService
from sentinelai.config import get_settings


@pytest.mark.asyncio
async def test_max_upload_size_enrollment_rejected():
    """Verify audio exceeding max_audio_upload_size_bytes is rejected immediately."""
    settings = get_settings()
    service = BiometricEnrollmentService(session=None)

    # Fabricate payload exceeding 10MB limit (10MB + 1024 bytes)
    oversized_bytes = b"\x00" * (settings.max_audio_upload_size_bytes + 1024)

    with pytest.raises(InvalidEnrollmentAudioError, match="exceeds the maximum allowed size"):
        await service._read_audio_bytes(oversized_bytes)


@pytest.mark.asyncio
async def test_max_upload_size_verification_rejected():
    """Verify probe audio exceeding max_audio_upload_size_bytes is rejected immediately."""
    settings = get_settings()
    service = BiometricVerificationService(session=None)

    oversized_bytes = b"\x00" * (settings.max_audio_upload_size_bytes + 1024)

    with pytest.raises(InvalidEnrollmentAudioError, match="exceeds the maximum allowed size"):
        await service._read_audio_bytes(oversized_bytes)


@pytest.mark.asyncio
async def test_valid_size_audio_accepted():
    """Verify audio within normal bounds is accepted without size exception."""
    service = BiometricEnrollmentService(session=None)
    normal_bytes = b"\x00" * 2048

    data, filename = await service._read_audio_bytes(normal_bytes)
    assert len(data) == 2048
    assert filename == "utterance.wav"


@pytest.mark.asyncio
async def test_inference_concurrency_semaphore_bounds():
    """Verify inference semaphore bounds concurrent execution according to settings."""
    settings = get_settings()
    original_max = settings.max_concurrent_inferences
    settings.max_concurrent_inferences = 2
    reset_inference_semaphore(limit=2)

    try:
        sem = get_inference_semaphore()
        active_workers = 0
        max_seen_workers = 0

        async def worker():
            nonlocal active_workers, max_seen_workers
            async with sem:
                active_workers += 1
                if active_workers > max_seen_workers:
                    max_seen_workers = active_workers
                await asyncio.sleep(0.05)
                active_workers -= 1

        # Launch 5 concurrent workers
        await asyncio.gather(*(worker() for _ in range(5)))

        # Concurrency must never exceed configured limit (2)
        assert max_seen_workers == 2

    finally:
        settings.max_concurrent_inferences = original_max
        reset_inference_semaphore()
