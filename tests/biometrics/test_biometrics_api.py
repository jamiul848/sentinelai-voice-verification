"""Integration tests for Biometric API endpoints (/api/v1/biometrics)."""

import pytest
from httpx import AsyncClient

from tests.biometrics.conftest import create_synthetic_wav_bytes


@pytest.mark.asyncio
async def test_api_enrollment_success(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify POST /api/v1/biometrics/enroll with 3 audio recordings."""
    files = [
        ("files", ("sample1.wav", create_synthetic_wav_bytes(duration_sec=2.0), "audio/wav")),
        ("files", ("sample2.wav", create_synthetic_wav_bytes(duration_sec=2.2), "audio/wav")),
        ("files", ("sample3.wav", create_synthetic_wav_bytes(duration_sec=2.4), "audio/wav")),
    ]

    response = await async_client.post(
        "/api/v1/biometrics/enroll",
        headers=auth_headers,
        files=files,
    )

    assert response.status_code == 201
    data = response.json()
    assert "profile_id" in data
    assert data["status"] == "ACTIVE"
    assert data["sample_count"] == 3
    assert len(data["samples"]) == 3
    assert data["mean_pairwise_similarity"] > 0.0


@pytest.mark.asyncio
async def test_api_enrollment_insufficient_samples(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Verify POST /api/v1/biometrics/enroll fails with fewer than 3 files."""
    files = [
        ("files", ("sample1.wav", create_synthetic_wav_bytes(), "audio/wav")),
        ("files", ("sample2.wav", create_synthetic_wav_bytes(), "audio/wav")),
    ]

    response = await async_client.post(
        "/api/v1/biometrics/enroll",
        headers=auth_headers,
        files=files,
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "INSUFFICIENT_ENROLLMENT_SAMPLES"


@pytest.mark.asyncio
async def test_api_enrollment_without_consent(
    async_client: AsyncClient,
    seeded_user,
):
    """Verify POST /api/v1/biometrics/enroll fails if user lacks biometric consent."""
    from sentinelai.auth.jwt_handler import create_access_token

    token = create_access_token(
        user_id=seeded_user.id,
        email=seeded_user.email,
        roles=["USER"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]

    response = await async_client.post(
        "/api/v1/biometrics/enroll",
        headers=headers,
        files=files,
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "BIOMETRIC_CONSENT_REQUIRED"


@pytest.mark.asyncio
async def test_api_enrollment_duplicate_active_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify enrolling twice returns 409 Conflict."""
    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]

    # First enrollment succeeds
    r1 = await async_client.post("/api/v1/biometrics/enroll", headers=auth_headers, files=files)
    assert r1.status_code == 201

    # Second enrollment fails with 409
    files_again = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    r2 = await async_client.post("/api/v1/biometrics/enroll", headers=auth_headers, files=files_again)
    assert r2.status_code == 409
    assert r2.json()["error_code"] == "ACTIVE_PROFILE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_api_verification_flow(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify live verification flow for genuine match and impostor probe."""
    # 1. Enroll
    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0), "audio/wav"))
        for i in range(3)
    ]
    await async_client.post("/api/v1/biometrics/enroll", headers=auth_headers, files=files)

    # 2. Genuine Probe -> MATCH
    genuine_file = ("file", ("probe_genuine.wav", create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0), "audio/wav"))
    r_genuine = await async_client.post(
        "/api/v1/biometrics/verify",
        headers=auth_headers,
        files=[genuine_file],
    )
    assert r_genuine.status_code == 200
    gen_data = r_genuine.json()
    assert gen_data["decision"] == "MATCH"
    assert gen_data["is_match"] is True
    assert gen_data["similarity_score"] >= gen_data["applied_threshold"]
    assert gen_data["threshold_version"] == "librispeech-dev-clean-eer-v1.0"
    assert gen_data["processing_time_ms"] > 0

    # 3. Impostor Probe -> NO_MATCH
    impostor_file = ("file", ("probe_impostor.wav", create_synthetic_wav_bytes(duration_sec=2.5, freq_hz=880.0), "audio/wav"))
    r_impostor = await async_client.post(
        "/api/v1/biometrics/verify",
        headers=auth_headers,
        files=[impostor_file],
    )
    assert r_impostor.status_code == 200
    imp_data = r_impostor.json()
    assert imp_data["decision"] == "NO_MATCH"
    assert imp_data["is_match"] is False
    assert imp_data["similarity_score"] < imp_data["applied_threshold"]


@pytest.mark.asyncio
async def test_api_verification_no_profile(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Verify POST /api/v1/biometrics/verify returns 404 when no profile is enrolled."""
    file = ("file", ("probe.wav", create_synthetic_wav_bytes(), "audio/wav"))
    response = await async_client.post(
        "/api/v1/biometrics/verify",
        headers=auth_headers,
        files=[file],
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "PROFILE_NOT_FOUND"


@pytest.mark.asyncio
async def test_api_get_active_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify GET /api/v1/biometrics/profile."""
    # Before enrollment -> 404
    r0 = await async_client.get("/api/v1/biometrics/profile", headers=auth_headers)
    assert r0.status_code == 404

    # Enroll
    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    await async_client.post("/api/v1/biometrics/enroll", headers=auth_headers, files=files)

    # After enrollment -> 200
    r1 = await async_client.get("/api/v1/biometrics/profile", headers=auth_headers)
    assert r1.status_code == 200
    data = r1.json()
    assert data["status"] == "ACTIVE"
    assert data["sample_count"] == 3
    assert len(data["enrollment_records"]) == 3


@pytest.mark.asyncio
async def test_api_re_enrollment(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify POST /api/v1/biometrics/profile/re-enroll."""
    files1 = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    r1 = await async_client.post("/api/v1/biometrics/enroll", headers=auth_headers, files=files1)
    original_id = r1.json()["profile_id"]

    # Re-enroll
    files2 = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    r2 = await async_client.post(
        "/api/v1/biometrics/profile/re-enroll",
        headers=auth_headers,
        files=files2,
    )
    assert r2.status_code == 201
    re_data = r2.json()
    assert re_data["profile_id"] != original_id
    assert re_data["previous_profile_id"] == original_id
    assert re_data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_api_revoke_profile(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify DELETE /api/v1/biometrics/profile."""
    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    await async_client.post("/api/v1/biometrics/enroll", headers=auth_headers, files=files)

    # Revoke
    r_del = await async_client.delete("/api/v1/biometrics/profile", headers=auth_headers)
    assert r_del.status_code == 200
    assert r_del.json()["status"] == "REVOKED"

    # Subsequent GET returns 404
    r_get = await async_client.get("/api/v1/biometrics/profile", headers=auth_headers)
    assert r_get.status_code == 404


@pytest.mark.asyncio
async def test_api_verification_history(
    async_client: AsyncClient,
    auth_headers: dict,
    seeded_threshold,
):
    """Verify GET /api/v1/biometrics/verification-history."""
    # Enroll
    files = [
        ("files", (f"sample{i}.wav", create_synthetic_wav_bytes(), "audio/wav"))
        for i in range(3)
    ]
    await async_client.post("/api/v1/biometrics/enroll", headers=auth_headers, files=files)

    # Run 1 verification
    file = ("file", ("probe.wav", create_synthetic_wav_bytes(), "audio/wav"))
    await async_client.post("/api/v1/biometrics/verify", headers=auth_headers, files=[file])

    # Query history
    r_hist = await async_client.get("/api/v1/biometrics/verification-history", headers=auth_headers)
    assert r_hist.status_code == 200
    data = r_hist.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
    assert data["items"][0]["decision"] in ("MATCH", "NO_MATCH")


@pytest.mark.asyncio
async def test_api_unauthorized_endpoints(async_client: AsyncClient):
    """Verify 401 Unauthorized when accessing biometric endpoints without credentials."""
    r_enroll = await async_client.post("/api/v1/biometrics/enroll")
    assert r_enroll.status_code == 401

    r_verify = await async_client.post("/api/v1/biometrics/verify")
    assert r_verify.status_code == 401

    r_profile = await async_client.get("/api/v1/biometrics/profile")
    assert r_profile.status_code == 401

    r_history = await async_client.get("/api/v1/biometrics/verification-history")
    assert r_history.status_code == 401
