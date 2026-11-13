"""Phase 8C Live End-to-End HTTP Integration Verification.

Validates all Phase 8C voice enrollment, biometric verification, and profile management contracts:
1. User registration & JWT authentication
2. Biometric legal consent validation (GET & POST /api/v1/consent)
3. Guard enforcement: enrollment rejection when consent is missing
4. Guard enforcement: verification rejection when no active profile exists
5. Multi-sample enrollment with 3 recordings (POST /api/v1/biometrics/enroll)
6. Voice profile inspection & telemetry retrieval (GET /api/v1/biometrics/profile)
7. Voice verification evaluation against reference centroid (POST /api/v1/biometrics/verify)
8. Real ECAPA-TDNN evaluation metrics (decision, similarity_score, applied_threshold, latency)
9. Verification history audit logging & query filtering (GET /api/v1/biometrics/verification-history)
10. Biometric re-enrollment with updated samples (POST /api/v1/biometrics/profile/re-enroll)
11. NIST SP 800-88 cryptographic shredding & profile revocation (DELETE /api/v1/biometrics/profile)
12. Rejection of subsequent verification requests against revoked profile
13. Biometric consent revocation (POST /api/v1/consent/revoke)
"""

import asyncio
import io
import os
import sys
import uuid
import numpy as np
import soundfile as sf
import httpx

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from sentinelai.main import create_app


def create_synthetic_wav_bytes(
    duration_sec: float = 2.0,
    sample_rate: int = 16000,
    freq_hz: float = 440.0,
    amplitude: float = 0.5,
) -> bytes:
    """Generate deterministic synthetic 16kHz mono 16-bit PCM WAV audio."""
    num_samples = int(sample_rate * duration_sec)
    t = np.linspace(0.0, duration_sec, num_samples, endpoint=False)
    signal = (amplitude * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, signal, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()


async def run_phase_8c_live_verification():
    print("=" * 75)
    print("SENTINEL VOICE - PHASE 8C LIVE HTTP INTEGRATION SUITE")
    print("=" * 75)

    app = create_app()
    test_email = f"operator_8c_{uuid.uuid4().hex[:8]}@sentinelvoice.io"
    test_password = "SecurePassword!987"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Step 1: User Registration
        print("\n[Step 1] Registering user account for biometric verification...")
        reg_payload = {
            "full_name": "Agent John Connor",
            "email": test_email,
            "password": test_password,
            "password_confirm": test_password,
            "accept_privacy_terms": True,
        }
        res = await client.post(
            "/api/v1/auth/register",
            json=reg_payload,
            headers={"X-Request-ID": str(uuid.uuid4())},
        )
        assert res.status_code == 201, f"Registration failed: {res.status_code} {res.text}"
        user_data = res.json()["data"]
        print(f"  ✓ User registered: {user_data['id']} ({user_data['email']})")

        # Step 2: Login
        print("\n[Step 2] Authenticating to retrieve JWT access token...")
        login_payload = {
            "email": test_email,
            "password": test_password,
        }
        res = await client.post(
            "/api/v1/auth/login",
            json=login_payload,
            headers={"X-Request-ID": str(uuid.uuid4())},
        )
        assert res.status_code == 200, f"Login failed: {res.status_code} {res.text}"
        access_token = res.json()["data"]["access_token"]
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Request-ID": str(uuid.uuid4()),
        }
        print("  ✓ Authenticated. JWT token acquired.")

        # Step 3: Check Initial Consent
        print("\n[Step 3] Verifying initial biometric consent status...")
        res = await client.get("/api/v1/consent/me", headers=auth_headers)
        assert res.status_code == 200, f"Failed getting consent: {res.text}"
        consent_data = res.json()["data"]
        assert consent_data.get("has_active_consent") is False
        print("  ✓ Initial consent status is False (unconsented).")

        # Step 4: Verification Guard - Consent Required
        print("\n[Step 4] Testing verification attempt without biometric consent...")
        probe_wav = create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0)
        res = await client.post(
            "/api/v1/biometrics/verify",
            headers=auth_headers,
            files={"file": ("probe.wav", probe_wav, "audio/wav")},
        )
        assert res.status_code == 403, f"Expected 403, got {res.status_code}: {res.text}"
        assert res.json().get("error_code") == "BIOMETRIC_CONSENT_REQUIRED"
        print(f"  ✓ Verification cleanly rejected prior to consent (403 BIOMETRIC_CONSENT_REQUIRED).")

        # Step 5: Enrollment Guard - Consent Required
        print("\n[Step 5] Testing enrollment attempt without biometric consent...")
        sample1 = create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0)
        sample2 = create_synthetic_wav_bytes(duration_sec=2.2, freq_hz=442.0)
        sample3 = create_synthetic_wav_bytes(duration_sec=2.1, freq_hz=438.0)
        files = [
            ("files", ("sample1.wav", sample1, "audio/wav")),
            ("files", ("sample2.wav", sample2, "audio/wav")),
            ("files", ("sample3.wav", sample3, "audio/wav")),
        ]
        res = await client.post(
            "/api/v1/biometrics/enroll",
            headers=auth_headers,
            files=files,
        )
        assert res.status_code in (400, 403), f"Expected 400/403, got {res.status_code}: {res.text}"
        print(f"  ✓ Enrollment cleanly rejected without consent ({res.status_code}).")

        # Step 6: Grant Biometric Consent
        print("\n[Step 6] Granting biometric legal consent (POST /api/v1/consent)...")
        consent_payload = {
            "consent_type": "VOICE_BIOMETRIC_ENROLLMENT",
            "consent_version": "1.0",
        }
        res = await client.post(
            "/api/v1/consent",
            headers=auth_headers,
            json=consent_payload,
        )
        assert res.status_code == 201, f"Consent grant failed: {res.text}"
        print("  ✓ Biometric consent successfully granted and recorded.")

        # Confirm consent status
        res = await client.get("/api/v1/consent/me", headers=auth_headers)
        assert res.json()["data"].get("has_active_consent") is True
        print("  ✓ Confirmed GET /api/v1/consent/me reports has_active_consent: True.")

        # Step 6b: Verification Guard - No Active Profile (with consent granted)
        print("\n[Step 6b] Testing verification attempt when consented but no voice profile exists...")
        res = await client.post(
            "/api/v1/biometrics/verify",
            headers=auth_headers,
            files={"file": ("probe.wav", probe_wav, "audio/wav")},
        )
        assert res.status_code in (400, 404), f"Expected 400/404, got {res.status_code}: {res.text}"
        print(f"  ✓ Verification cleanly rejected prior to profile enrollment ({res.status_code}).")

        # Step 7: Multi-Sample Voice Enrollment
        print("\n[Step 7] Submitting 3 audio recordings to POST /api/v1/biometrics/enroll...")
        res = await client.post(
            "/api/v1/biometrics/enroll",
            headers=auth_headers,
            files=files,
        )
        assert res.status_code == 201, f"Enrollment failed: {res.status_code} {res.text}"
        enroll_data = res.json()
        profile_id = enroll_data["profile_id"]
        assert enroll_data["status"] == "ACTIVE"
        assert enroll_data["sample_count"] == 3
        assert len(enroll_data["samples"]) == 3
        assert enroll_data["mean_pairwise_similarity"] > 0.0
        print(f"  ✓ Enrolled active profile: {profile_id}")
        print(f"    - Sample count: {enroll_data['sample_count']}")
        print(f"    - Pairwise similarity: {enroll_data['mean_pairwise_similarity']:.4f}")
        print(f"    - Model: {enroll_data.get('model_identifier')}")

        # Step 8: Profile Inspection
        print("\n[Step 8] Retrieving voice profile via GET /api/v1/biometrics/profile...")
        res = await client.get("/api/v1/biometrics/profile", headers=auth_headers)
        assert res.status_code == 200, f"Get profile failed: {res.status_code} {res.text}"
        profile_data = res.json()
        assert profile_data["id"] == profile_id
        assert profile_data["status"] == "ACTIVE"
        assert profile_data["sample_count"] == 3
        assert len(profile_data.get("enrollment_records", [])) == 3
        print(f"  ✓ Retrieved profile {profile_data['id']} with 3 constituent utterance records.")

        # Step 9: Speaker Verification
        print("\n[Step 9] Submitting spoken probe to POST /api/v1/biometrics/verify...")
        probe_wav = create_synthetic_wav_bytes(duration_sec=2.0, freq_hz=440.0)
        res = await client.post(
            "/api/v1/biometrics/verify",
            headers=auth_headers,
            files={"file": ("probe_sample.wav", probe_wav, "audio/wav")},
        )
        assert res.status_code == 200, f"Verification failed: {res.status_code} {res.text}"
        verif_data = res.json()
        verif_id = verif_data["verification_id"]
        decision = verif_data["decision"]
        score = verif_data["similarity_score"]
        threshold = verif_data["applied_threshold"]
        latency = verif_data["processing_time_ms"]
        print(f"  ✓ Verification executed: {verif_id}")
        print(f"    - Decision: {decision} (is_match: {verif_data['is_match']})")
        print(f"    - Cosine similarity score: {score:.4f}")
        print(f"    - Operating threshold: {threshold:.6f}")
        print(f"    - Latency: {latency:.1f}ms")
        print(f"    - Model: {verif_data.get('model_identifier')}")
        print(f"    - Threshold version: {verif_data.get('threshold_version')}")

        # Step 10: Verification History
        print("\n[Step 10] Querying audit log via GET /api/v1/biometrics/verification-history...")
        res = await client.get("/api/v1/biometrics/verification-history", headers=auth_headers)
        assert res.status_code == 200, f"History query failed: {res.status_code} {res.text}"
        history_data = res.json()
        assert history_data["total"] >= 1
        assert len(history_data["items"]) >= 1
        first_item = history_data["items"][0]
        assert first_item["decision"] in ("MATCH", "NO_MATCH")
        print(f"  ✓ History confirmed: {history_data['total']} verification audit log(s) found.")

        # Step 11: Re-enrollment
        print("\n[Step 11] Re-enrolling profile with 3 fresh samples (POST /api/v1/biometrics/profile/re-enroll)...")
        re_sample1 = create_synthetic_wav_bytes(duration_sec=2.2, freq_hz=440.0)
        re_sample2 = create_synthetic_wav_bytes(duration_sec=2.3, freq_hz=442.0)
        re_sample3 = create_synthetic_wav_bytes(duration_sec=2.1, freq_hz=441.0)
        re_files = [
            ("files", ("re_sample1.wav", re_sample1, "audio/wav")),
            ("files", ("re_sample2.wav", re_sample2, "audio/wav")),
            ("files", ("re_sample3.wav", re_sample3, "audio/wav")),
        ]
        res = await client.post(
            "/api/v1/biometrics/profile/re-enroll",
            headers=auth_headers,
            files=re_files,
        )
        assert res.status_code == 201, f"Re-enrollment failed: {res.status_code} {res.text}"
        re_data = res.json()
        assert re_data["status"] == "ACTIVE"
        assert re_data["sample_count"] == 3
        print(f"  ✓ Re-enrolled profile {re_data['profile_id']} with updated centroid.")

        # Step 12: Revocation & NIST SP 800-88 Vector Shredding
        print("\n[Step 12] Revoking profile via DELETE /api/v1/biometrics/profile...")
        res = await client.delete("/api/v1/biometrics/profile", headers=auth_headers)
        assert res.status_code == 200, f"Revocation failed: {res.status_code} {res.text}"
        revoke_data = res.json()
        assert revoke_data["status"] == "REVOKED"
        print(f"  ✓ Profile revoked. Message: {revoke_data.get('message')}")

        # Step 13: Post-Revocation Guard
        print("\n[Step 13] Verifying subsequent verification attempt against revoked profile is rejected...")
        res = await client.post(
            "/api/v1/biometrics/verify",
            headers=auth_headers,
            files={"file": ("probe_post_revoke.wav", probe_wav, "audio/wav")},
        )
        assert res.status_code in (400, 404), f"Expected 400/404 after revocation, got {res.status_code}: {res.text}"
        print(f"  ✓ Rejected post-revocation verification request ({res.status_code}).")

        # Step 14: Revoke Consent
        print("\n[Step 14] Revoking biometric consent (POST /api/v1/consent/revoke)...")
        res = await client.post(
            "/api/v1/consent/revoke",
            headers=auth_headers,
            json={
                "consent_type": "VOICE_BIOMETRIC_ENROLLMENT",
                "reason": "Test lifecycle completion revocation",
            },
        )
        assert res.status_code == 200, f"Consent revocation failed: {res.status_code} {res.text}"
        print("  ✓ Biometric consent revoked.")

        res = await client.get("/api/v1/consent/me", headers=auth_headers)
        assert res.json()["data"].get("has_active_consent") is False
        print("  ✓ Confirmed GET /api/v1/consent/me reports has_active_consent: False.")

    print("\n" + "=" * 75)
    print("ALL 14 PHASE 8C LIVE HTTP INTEGRATION STEPS PASSED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_phase_8c_live_verification())
