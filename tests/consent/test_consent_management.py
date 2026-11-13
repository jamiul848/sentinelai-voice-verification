"""Integration tests for biometric legal consent workflows and GDPR/BIPA compliance."""

from pathlib import Path
import pytest
from httpx import AsyncClient

from sentinelai.database.repositories.profile_repository import ProfileRepository


@pytest.mark.asyncio
async def test_grant_and_view_consent(async_client: AsyncClient, seeded_user):
    """Verify granting explicit consent and viewing the active status and history."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initially no consent
    r0 = await async_client.get("/api/v1/consent/me", headers=headers)
    assert r0.status_code == 200
    assert r0.json()["data"]["has_active_consent"] is False

    # Grant consent v1.0
    r1 = await async_client.post(
        "/api/v1/consent",
        json={"consent_version": "1.0", "consent_type": "VOICE_BIOMETRIC_ENROLLMENT"},
        headers=headers,
    )
    assert r1.status_code == 201
    assert r1.json()["data"]["consent_granted"] is True

    # View consent: active
    r2 = await async_client.get("/api/v1/consent/me", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["data"]["has_active_consent"] is True
    assert len(r2.json()["data"]["history"]) == 1


@pytest.mark.asyncio
async def test_revoke_consent_and_shred_profile(
    async_client: AsyncClient,
    seeded_user,
    test_session,
    tmp_path: Path,
):
    """Verify that revoking consent revokes active voice profile and securely deletes the vector file."""
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Grant consent
    await async_client.post(
        "/api/v1/consent",
        json={"consent_version": "1.0", "consent_type": "VOICE_BIOMETRIC_ENROLLMENT"},
        headers=headers,
    )

    # 2. Simulate an existing active voice profile with a dummy vector file
    vector_file = tmp_path / f"test_embedding_{seeded_user.id}.enc"
    vector_file.write_bytes(b"Simulated_AES_256_GCM_Encrypted_Vector_Data_1234567890")
    assert vector_file.exists()

    profile_repo = ProfileRepository(test_session)
    profile = await profile_repo.create_profile(
        user_id=seeded_user.id,
        sample_count=3,
        mean_pairwise_similarity=0.85,
        embedding_storage_path=str(vector_file),
        embedding_sha256="abc123sha256",
    )
    await test_session.commit()
    assert profile.status == "ACTIVE"

    # 3. User revokes consent
    revoke_res = await async_client.post(
        "/api/v1/consent/revoke",
        json={"consent_type": "VOICE_BIOMETRIC_ENROLLMENT", "reason": "User requested data deletion"},
        headers=headers,
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["data"]["consent_granted"] is False

    # 4. Invariant: Active profile is marked REVOKED in database
    refreshed_profile = await profile_repo.get_profile_by_id(profile.id)
    assert refreshed_profile.status == "REVOKED"
    assert refreshed_profile.revoked_at is not None

    # 5. Invariant: Vector file has been securely shredded and removed from disk
    assert not vector_file.exists()

    # 6. Consent history preserves both the grant and revocation records
    status_res = await async_client.get("/api/v1/consent/me", headers=headers)
    assert status_res.json()["data"]["has_active_consent"] is False
    assert len(status_res.json()["data"]["history"]) == 2

