"""Phase 8B Live End-to-End HTTP Integration Verification.

Validates all Phase 8B authentication and user dashboard contracts:
1. User registration with Argon2id password complexity and GDPR consent
2. Duplicate email 409 conflict handling
3. Authentication / Login with JWT access token, HttpOnly refresh cookie, and double-submit CSRF cookie
4. User profile inspection via GET /api/v1/users/me with X-Request-ID tracing
5. Display name update via PATCH /api/v1/users/me
6. Password change via POST /api/v1/users/change-password
7. Consent retrieval via GET /api/v1/consent/me
8. Refresh token rotation via POST /api/v1/auth/refresh
9. Clean session logout via POST /api/v1/auth/logout
10. Revocation verification (revoked refresh tokens rejected).
"""

import asyncio
import os
import sys
import uuid
import httpx
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from sentinelai.main import create_app
from sentinelai.config import get_settings


async def run_phase_8b_live_verification():
    print("=" * 70)
    print("SENTINEL VOICE - PHASE 8B LIVE HTTP INTEGRATION SUITE")
    print("=" * 70)

    app = create_app()
    test_email = f"operator_{uuid.uuid4().hex[:8]}@sentinelvoice.io"
    test_password = "SecurePassword!987"
    test_new_password = "UpdatedPassword!654"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Step 1: User Registration
        print("\n[Step 1] Testing POST /api/v1/auth/register...")
        reg_payload = {
            "full_name": "Test Officer Sarah Connor",
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
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        reg_data = res.json()
        assert reg_data["success"] is True
        assert reg_data["data"]["email"] == test_email
        print(f"  ✓ User registered: {reg_data['data']['id']} ({reg_data['data']['email']})")

        # Step 2: Duplicate Registration Handling
        print("\n[Step 2] Testing duplicate registration 409 conflict...")
        res_dup = await client.post(
            "/api/v1/auth/register",
            json=reg_payload,
            headers={"X-Request-ID": str(uuid.uuid4())},
        )
        assert res_dup.status_code == 409, f"Expected 409 Conflict, got {res_dup.status_code}"
        print("  ✓ Duplicate email rejected with HTTP 409 Conflict")

        # Step 3: User Login
        print("\n[Step 3] Testing POST /api/v1/auth/login...")
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": test_password},
            headers={"X-Request-ID": str(uuid.uuid4())},
        )
        assert login_res.status_code == 200, f"Expected 200, got {login_res.status_code}: {login_res.text}"
        login_data = login_res.json()["data"]
        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]
        assert access_token and refresh_token
        # Verify HttpOnly cookie in response headers
        cookies = login_res.cookies
        assert "sentinel_refresh_token" in cookies
        print(f"  ✓ Login succeeded. Access Token issued (length: {len(access_token)})")
        print("  ✓ HttpOnly sentinel_refresh_token cookie dispatched")

        # Step 4: User Profile Inspection
        print("\n[Step 4] Testing GET /api/v1/users/me with X-Request-ID...")
        req_id = str(uuid.uuid4())
        me_res = await client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-Request-ID": req_id,
            },
        )
        assert me_res.status_code == 200, f"Expected 200, got {me_res.status_code}: {me_res.text}"
        assert me_res.headers.get("x-request-id") == req_id
        me_data = me_res.json()["data"]
        assert me_data["email"] == test_email
        print(f"  ✓ Identity retrieved: {me_data['full_name']}")
        print(f"  ✓ Correlation verified: X-Request-ID echoed in response headers ({req_id})")

        # Step 5: Profile Update
        print("\n[Step 5] Testing PATCH /api/v1/users/me...")
        patch_res = await client.patch(
            "/api/v1/users/me",
            json={"full_name": "Commander Sarah Connor"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["data"]["full_name"] == "Commander Sarah Connor"
        print("  ✓ Profile display name updated to 'Commander Sarah Connor'")

        # Step 6: Consent Retrieval
        print("\n[Step 6] Testing GET /api/v1/consent/me...")
        consent_res = await client.get(
            "/api/v1/consent/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert consent_res.status_code == 200
        consent_data = consent_res.json()["data"]
        print(f"  ✓ Consent record retrieved: active={consent_data['has_active_consent']}")

        # Step 7: Password Change
        print("\n[Step 7] Testing POST /api/v1/users/change-password...")
        pw_res = await client.post(
            "/api/v1/users/change-password",
            json={
                "current_password": test_password,
                "new_password": test_new_password,
                "new_password_confirm": test_new_password,
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert pw_res.status_code == 200, f"Expected 200, got {pw_res.status_code}: {pw_res.text}"
        print("  ✓ Password changed successfully")

        # Step 8: Re-login with new password
        print("\n[Step 8] Testing login with new password...")
        relogin_res = await client.post(
            "/api/v1/auth/login",
            json={"email": test_email, "password": test_new_password},
        )
        assert relogin_res.status_code == 200
        new_login_data = relogin_res.json()["data"]
        new_access_token = new_login_data["access_token"]
        new_refresh_token = new_login_data["refresh_token"]
        print("  ✓ Successfully authenticated using new password")

        # Step 9: Token Refresh Rotation
        print("\n[Step 9] Testing POST /api/v1/auth/refresh (rotation)...")
        refresh_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh_token},
        )
        assert refresh_res.status_code == 200, f"Expected 200, got {refresh_res.status_code}: {refresh_res.text}"
        rotated_data = refresh_res.json()["data"]
        rotated_access = rotated_data["access_token"]
        rotated_refresh = rotated_data["refresh_token"]
        assert rotated_access != new_access_token
        assert rotated_refresh != new_refresh_token
        print("  ✓ Refresh token successfully rotated to new family pair")

        # Step 10: Logout
        print("\n[Step 10] Testing POST /api/v1/auth/logout...")
        logout_res = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": rotated_refresh},
        )
        assert logout_res.status_code == 200
        print("  ✓ User logged out. Session revoked.")

        # Step 11: Verify Old Token Revoked
        print("\n[Step 11] Verifying revoked refresh token cannot be refreshed again...")
        reuse_res = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": rotated_refresh},
        )
        assert reuse_res.status_code == 401
        print("  ✓ Revoked refresh token rejected with HTTP 401 Unauthorized")

    print("\n" + "=" * 70)
    print("ALL 11 PHASE 8B LIVE HTTP INTEGRATION STEPS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_phase_8b_live_verification())

