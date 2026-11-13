"""Security tests for voice biometrics pipeline (zero-trust, isolation, tamper defense)."""

from pathlib import Path
import pytest
from httpx import AsyncClient

from sentinelai.biometrics.exceptions import (
    DirectoryTraversalError,
    VectorTamperedError,
)
from sentinelai.biometrics.storage import BiometricStorageManager
from tests.biometrics.conftest import create_synthetic_wav_bytes


@pytest.mark.asyncio
async def test_cross_user_isolation(
    async_client: AsyncClient,
    auth_headers: dict,
    second_auth_headers: dict,
    seeded_threshold,
):
    """Verify that User B cannot view, verify against, or mutate User A's profile."""
    # User A enrolls
    files_a = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    r_enroll_a = await async_client.post(
        "/api/v1/biometrics/enroll",
        headers=auth_headers,
        files=files_a,
    )
    assert r_enroll_a.status_code == 201
    profile_id_a = r_enroll_a.json()["profile_id"]

    # User B queries their profile -> must return 404 Not Found (not User A's profile)
    r_profile_b = await async_client.get("/api/v1/biometrics/profile", headers=second_auth_headers)
    assert r_profile_b.status_code == 404

    # User B tries to delete their profile -> 404 Not Found (User A's profile is unharmed)
    r_del_b = await async_client.delete("/api/v1/biometrics/profile", headers=second_auth_headers)
    assert r_del_b.status_code == 404

    # Verify User A's profile is still intact and ACTIVE
    r_profile_a = await async_client.get("/api/v1/biometrics/profile", headers=auth_headers)
    assert r_profile_a.status_code == 200
    assert r_profile_a.json()["id"] == profile_id_a
    assert r_profile_a.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_tamper_detection_in_live_verification(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
    tmp_path: Path,
):
    """Verify that bit-flipping an enrolled vector file causes verification to fail with 500 VECTOR_TAMPERED."""
    # 1. Enroll User
    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    r_enroll = await async_client.post(
        "/api/v1/biometrics/enroll",
        headers=auth_headers,
        files=files,
    )
    assert r_enroll.status_code == 201

    # 2. Locate container file on disk and tamper with it
    from sentinelai.config import get_settings

    settings = get_settings()
    store_dir = Path(settings.biometric_store_path)
    enc_files = list(store_dir.rglob("*.enc"))
    assert len(enc_files) >= 1
    target_file = enc_files[0]

    with open(target_file, "r+b") as f:
        f.seek(20)
        byte = f.read(1)
        f.seek(20)
        f.write(bytes([byte[0] ^ 0xFF]))

    # 3. Verification must fail due to checksum/GCM tag mismatch
    probe = ("file", ("probe.wav", create_synthetic_wav_bytes(), "audio/wav"))
    r_verif = await async_client.post(
        "/api/v1/biometrics/verify",
        headers=auth_headers,
        files=[probe],
    )
    assert r_verif.status_code == 500
    assert r_verif.json()["error_code"] == "VECTOR_TAMPERED"


@pytest.mark.asyncio
async def test_consent_revocation_blocks_verification(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify that revoking consent immediately disables biometric verification."""
    # 1. Enroll
    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    r_enroll = await async_client.post(
        "/api/v1/biometrics/enroll",
        headers=auth_headers,
        files=files,
    )
    assert r_enroll.status_code == 201

    # 2. Revoke Consent via consent API
    r_revoke = await async_client.post(
        "/api/v1/consent/revoke",
        headers=auth_headers,
        json={"consent_type": "VOICE_BIOMETRIC_ENROLLMENT"},
    )
    assert r_revoke.status_code == 200

    # 3. Verification must be blocked with 403 Forbidden
    probe = ("file", ("probe.wav", create_synthetic_wav_bytes(), "audio/wav"))
    r_verif = await async_client.post(
        "/api/v1/biometrics/verify",
        headers=auth_headers,
        files=[probe],
    )
    assert r_verif.status_code == 403
    assert r_verif.json()["error_code"] == "BIOMETRIC_CONSENT_REQUIRED"

