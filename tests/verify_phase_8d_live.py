"""Phase 8D Live End-to-End HTTP Integration Verification.

Validates all Phase 8D Administrator Console and System Monitoring contracts:
1. Standard Operator Registration & Login
2. Authoritative RBAC Rejection (403 Forbidden) for Non-Admins across all admin routes:
   - GET /api/v1/admin/overview
   - GET /api/v1/admin/users
   - GET /api/v1/admin/voice-profiles
   - GET /api/v1/admin/analytics
   - GET /api/v1/admin/thresholds
   - POST /api/v1/admin/thresholds
   - GET /api/v1/admin/audit-logs
   - GET /api/v1/admin/security-events
   - GET /health/detailed
3. Admin Operator Registration, RBAC Promotion, & Authentication
4. Fleet Overview Statistics Retrieval (GET /api/v1/admin/overview)
5. User Roster & Biometric Flag Inspection (GET /api/v1/admin/users)
6. Single User Inspection without Password Hash Leakage (GET /api/v1/admin/users/{id})
7. Account Lifecycle State Mutation (PATCH /api/v1/admin/users/{id}/status)
8. Role Assignment Governance (PATCH /api/v1/admin/users/{id}/roles)
9. Voice Profile Registry without Raw Vector/Audio Leakage (GET /api/v1/admin/voice-profiles)
10. Biometric Verification Performance Analytics (GET /api/v1/admin/analytics)
11. Registered Decision Threshold Querying (GET /api/v1/admin/thresholds)
12. Registration of New Calibrated Threshold (POST /api/v1/admin/thresholds)
13. Cosine Range Bound Enforcement [-1.0, 1.0] (422 Rejection on Invalid Boundary)
14. Threshold Activation & Engine Synchronization (POST /api/v1/admin/thresholds/{id}/activate)
15. Active Operating Boundary Inspection (GET /api/v1/admin/thresholds/active)
16. Immutable Global Audit Log Ledger Inspection (GET /api/v1/admin/audit-logs)
17. Security Events & Rate Limiter Telemetry (GET /api/v1/admin/security-events)
18. Detailed Diagnostic Health Probes (GET /health/detailed)
19. Disposable User Lifecycle Deletion (DELETE /api/v1/admin/users/{id})
"""

import asyncio
import os
import sys
import uuid
import httpx

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from sentinelai.main import create_app
from sentinelai.database.connection import get_session_factory
from sentinelai.database.repositories.user_repository import UserRepository


async def run_phase_8d_live_verification():
    print("=" * 75)
    print("SENTINEL VOICE - PHASE 8D LIVE HTTP INTEGRATION SUITE")
    print("=" * 75)

    app = create_app()

    standard_email = f"operator_std_{uuid.uuid4().hex[:8]}@sentinelvoice.io"
    admin_email = f"operator_adm_{uuid.uuid4().hex[:8]}@sentinelvoice.io"
    disposable_email = f"operator_disp_{uuid.uuid4().hex[:8]}@sentinelvoice.io"
    test_password = "SecurePassword!987"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # ----------------------------------------------------------------------
        # Step 1: Standard User Registration & Login
        # ----------------------------------------------------------------------
        print("\n[Step 1] Registering standard user account...")
        reg_payload = {
            "full_name": "Standard Operator",
            "email": standard_email,
            "password": test_password,
            "password_confirm": test_password,
            "accept_privacy_terms": True,
        }
        res = await client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201, f"Standard user registration failed: {res.text}"
        std_user = res.json()["data"]
        print(f"  ✓ Standard user registered: {std_user['id']} ({std_user['email']})")

        print("  Authenticating standard user...")
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": standard_email, "password": test_password},
        )
        assert res.status_code == 200, f"Standard user login failed: {res.text}"
        std_token = res.json()["data"]["access_token"]
        std_headers = {"Authorization": f"Bearer {std_token}"}
        print("  ✓ Standard JWT token acquired.")

        # ----------------------------------------------------------------------
        # Step 2: Authoritative RBAC Access Denial (403 Forbidden)
        # ----------------------------------------------------------------------
        print("\n[Step 2] Verifying Authoritative FastAPI Backend RBAC Guard (403)...")
        forbidden_endpoints = [
            ("GET", "/api/v1/admin/overview", None),
            ("GET", "/api/v1/admin/users", None),
            ("GET", "/api/v1/admin/voice-profiles", None),
            ("GET", "/api/v1/admin/analytics", None),
            ("GET", "/api/v1/admin/thresholds", None),
            ("POST", "/api/v1/admin/thresholds", {
                "version_tag": "illegal-v1",
                "threshold_value": 0.40,
                "calibration_dataset": "none",
            }),
            ("GET", "/api/v1/admin/audit-logs", None),
            ("GET", "/api/v1/admin/security-events", None),
            ("GET", "/health/detailed", None),
        ]

        for method, path, json_body in forbidden_endpoints:
            if method == "GET":
                res = await client.get(path, headers=std_headers)
            else:
                res = await client.post(path, headers=std_headers, json=json_body)
            assert res.status_code == 403, f"Expected 403 for {method} {path}, got {res.status_code}: {res.text}"
            print(f"  ✓ RBAC securely rejected {method} {path} (403 Forbidden)")

        # ----------------------------------------------------------------------
        # Step 3: Admin User Registration & Role Elevation
        # ----------------------------------------------------------------------
        print("\n[Step 3] Registering admin user and elevating to ADMIN role...")
        res = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Admin Operator",
                "email": admin_email,
                "password": test_password,
                "password_confirm": test_password,
                "accept_privacy_terms": True,
            },
        )
        assert res.status_code == 201, f"Admin user registration failed: {res.text}"
        admin_user_id = uuid.UUID(res.json()["data"]["id"])

        # Elevate to ADMIN in DB
        session_factory = get_session_factory()
        async with session_factory() as session:
            user_repo = UserRepository(session)
            admin_role = await user_repo.get_role_by_name("ADMIN")
            if not admin_role:
                admin_role = await user_repo.create_role(name="ADMIN", description="Administrator")
            await user_repo.assign_role(admin_user_id, admin_role.id)
            await session.commit()
        print(f"  ✓ Elevated user {admin_user_id} to ADMIN in PostgreSQL.")

        # Login as Admin
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": test_password},
        )
        assert res.status_code == 200, f"Admin user login failed: {res.text}"
        admin_token = res.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("  ✓ Admin JWT access token acquired with ADMIN claims.")

        # ----------------------------------------------------------------------
        # Step 4: Platform Overview Statistics
        # ----------------------------------------------------------------------
        print("\n[Step 4] Testing GET /api/v1/admin/overview...")
        res = await client.get("/api/v1/admin/overview", headers=admin_headers)
        assert res.status_code == 200, f"Admin overview failed: {res.text}"
        overview = res.json()["data"]
        assert "users" in overview
        assert "voice_profiles" in overview
        assert "verifications" in overview
        assert "system_health" in overview
        assert overview["users"]["total"] >= 2
        print(f"  ✓ Platform Overview: {overview['users']['total']} users, "
              f"{overview['voice_profiles']['total']} profiles, "
              f"DB: {overview['system_health']['database_status']}")

        # ----------------------------------------------------------------------
        # Step 5: User Fleet Management & Inspector
        # ----------------------------------------------------------------------
        print("\n[Step 5] Testing GET /api/v1/admin/users...")
        res = await client.get("/api/v1/admin/users", headers=admin_headers)
        assert res.status_code == 200, f"List users failed: {res.text}"
        users_list = res.json()["data"]
        assert len(users_list) >= 2
        std_record = next(u for u in users_list if u["email"] == standard_email)
        assert "id" in std_record
        assert "email" in std_record
        assert "roles" in std_record
        assert "is_active" in std_record
        print(f"  ✓ User roster retrieved ({len(users_list)} accounts). Standard user email: {std_record['email']}")

        print("\n[Step 6] Testing single user details inspector (GET /api/v1/admin/users/{id})...")
        res = await client.get(f"/api/v1/admin/users/{std_record['id']}", headers=admin_headers)
        assert res.status_code == 200, f"Get user details failed: {res.text}"
        user_detail = res.json()["data"]
        assert "hashed_password" not in user_detail
        assert "password" not in user_detail
        print("  ✓ Single user inspected: Zero credential leakage verified.")

        # ----------------------------------------------------------------------
        # Step 6: User Status & Role Mutations
        # ----------------------------------------------------------------------
        print("\n[Step 7] Testing PATCH /api/v1/admin/users/{id}/status (Suspension & Reactivation)...")
        res = await client.patch(
            f"/api/v1/admin/users/{std_record['id']}/status",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert res.status_code == 200, f"Deactivate failed: {res.text}"
        assert res.json()["data"]["is_active"] is False
        print("  ✓ Account deactivated.")

        # Reactivate account
        res = await client.patch(
            f"/api/v1/admin/users/{std_record['id']}/status",
            headers=admin_headers,
            json={"is_active": True},
        )
        assert res.status_code == 200, f"Reactivate failed: {res.text}"
        assert res.json()["data"]["is_active"] is True
        print("  ✓ Account reactivated.")

        print("\n[Step 8] Testing PATCH /api/v1/admin/users/{id}/roles...")
        res = await client.patch(
            f"/api/v1/admin/users/{std_record['id']}/roles",
            headers=admin_headers,
            json={"roles": ["USER"]},
        )
        assert res.status_code == 200, f"Update roles failed: {res.text}"
        assert "USER" in res.json()["data"]["roles"]
        print("  ✓ RBAC roles updated.")

        # ----------------------------------------------------------------------
        # Step 7: Voice Profile Registry
        # ----------------------------------------------------------------------
        print("\n[Step 9] Testing GET /api/v1/admin/voice-profiles...")
        res = await client.get("/api/v1/admin/voice-profiles", headers=admin_headers)
        assert res.status_code == 200, f"Voice profiles list failed: {res.text}"
        profile_data = res.json()["data"]
        assert "items" in profile_data
        for p in profile_data["items"]:
            assert "embedding_path" not in p
            assert "embedding" not in p
            assert "vector" not in p
        print(f"  ✓ Voice Profile Registry inspected: Zero embedding vector leakage verified.")

        # ----------------------------------------------------------------------
        # Step 8: Verification Analytics
        # ----------------------------------------------------------------------
        print("\n[Step 10] Testing GET /api/v1/admin/analytics?days=7...")
        res = await client.get("/api/v1/admin/analytics?days=7", headers=admin_headers)
        assert res.status_code == 200, f"Analytics failed: {res.text}"
        analytics = res.json()["data"]
        assert "total_verifications" in analytics
        assert "match_rate" in analytics
        assert "average_latency_ms" in analytics
        assert "timeline" in analytics
        print(f"  ✓ Verification Analytics: Total={analytics['total_verifications']}, "
              f"MatchRate={analytics['match_rate']}%, AvgLatency={analytics['average_latency_ms']}ms")

        # ----------------------------------------------------------------------
        # Step 9: Dynamic Threshold Governance
        # ----------------------------------------------------------------------
        print("\n[Step 11] Testing GET /api/v1/admin/thresholds...")
        res = await client.get("/api/v1/admin/thresholds", headers=admin_headers)
        assert res.status_code == 200, f"List thresholds failed: {res.text}"
        initial_thresholds = res.json()["data"]
        print(f"  ✓ Found {len(initial_thresholds)} existing threshold configuration(s).")

        print("\n[Step 12] Testing Cosine Validation on Threshold Creation (POST /api/v1/admin/thresholds)...")
        invalid_res = await client.post(
            "/api/v1/admin/thresholds",
            headers=admin_headers,
            json={
                "version_tag": "invalid-cosine-v99",
                "threshold_value": 1.45,  # Exceeds max cosine bound of 1.0
                "calibration_dataset": "Invalid Test",
            },
        )
        assert invalid_res.status_code == 422, f"Expected 422 for cosine > 1.0, got {invalid_res.status_code}: {invalid_res.text}"
        print("  ✓ Threshold rejected for cosine > 1.0 (422 Unprocessable Entity)")

        print("\n[Step 13] Registering valid calibrated threshold...")
        new_tag = f"voxceleb-phase8d-{uuid.uuid4().hex[:6]}"
        create_res = await client.post(
            "/api/v1/admin/thresholds",
            headers=admin_headers,
            json={
                "version_tag": new_tag,
                "threshold_value": 0.425000,
                "calibration_dataset": "LibriSpeech dev-clean + VoxCeleb1",
                "calibration_criterion": "EER Minimization",
                "model_identifier": "speechbrain/spkrec-ecapa-voxceleb",
                "calibration_metadata": {"reported_eer": 0.0125},
            },
        )
        assert create_res.status_code == 201, f"Create threshold failed: {create_res.text}"
        new_thresh = create_res.json()["data"]
        assert new_thresh["version_tag"] == new_tag
        assert new_thresh["threshold_value"] == 0.425
        assert new_thresh["is_active"] is False
        print(f"  ✓ Calibrated threshold registered: {new_thresh['id']} ({new_thresh['version_tag']})")

        print("\n[Step 14] Activating operational decision boundary...")
        act_res = await client.post(
            f"/api/v1/admin/thresholds/{new_thresh['id']}/activate",
            headers=admin_headers,
        )
        assert act_res.status_code == 200, f"Activate threshold failed: {act_res.text}"
        assert act_res.json()["data"]["is_active"] is True
        print(f"  ✓ Threshold {new_thresh['id']} activated.")

        print("\n[Step 15] Verifying active threshold query (GET /api/v1/admin/thresholds/active)...")
        active_res = await client.get("/api/v1/admin/thresholds/active", headers=admin_headers)
        assert active_res.status_code == 200, f"Get active threshold failed: {active_res.text}"
        active_config = active_res.json()["data"]
        assert active_config["id"] == new_thresh["id"]
        assert active_config["version_tag"] == new_tag
        print(f"  ✓ Verified active threshold matches: {active_config['version_tag']} (Cosine: {active_config['threshold_value']})")

        # ----------------------------------------------------------------------
        # Step 10: Audit Logs & Security Events
        # ----------------------------------------------------------------------
        print("\n[Step 16] Testing GET /api/v1/admin/audit-logs...")
        res = await client.get("/api/v1/admin/audit-logs", headers=admin_headers)
        assert res.status_code == 200, f"Audit logs failed: {res.text}"
        logs_data = res.json()["data"]
        assert "items" in logs_data
        assert len(logs_data["items"]) > 0
        for l in logs_data["items"]:
            payload = l.get("payload") or {}
            assert "password" not in str(payload).lower()
            assert "access_token" not in str(payload).lower()
            assert "refresh_token" not in str(payload).lower()
        print(f"  ✓ Audit Ledger inspected ({len(logs_data['items'])} events): Zero credential leakage verified.")

        print("\n[Step 17] Testing GET /api/v1/admin/security-events...")
        res = await client.get("/api/v1/admin/security-events", headers=admin_headers)
        assert res.status_code == 200, f"Security events failed: {res.text}"
        sec_data = res.json()["data"]
        assert "rate_limiter" in sec_data
        assert "backend" in sec_data["rate_limiter"]
        print(f"  ✓ Security Events: Rate limiter backend: {sec_data['rate_limiter']['backend']}")

        # ----------------------------------------------------------------------
        # Step 11: System Diagnostic Health Probes
        # ----------------------------------------------------------------------
        print("\n[Step 18] Testing GET /health/detailed with Admin Authorization...")
        res = await client.get("/health/detailed", headers=admin_headers)
        assert res.status_code == 200, f"Detailed health failed: {res.text}"
        health = res.json()
        assert health["status"] in ["ready", "healthy"]
        assert "components" in health
        assert "database" in health["components"]
        assert "ecapa_engine" in health
        assert "biometric_storage" in health
        assert "encryption_service" in health
        is_loaded = health['ecapa_engine'].get('loaded', health['ecapa_engine'].get('is_loaded', False))
        print(f"  ✓ Diagnostic Health Probes: DB Status={health['components']['database']['status']}, "
              f"ECAPA Model Loaded={is_loaded}, "
              f"Storage Vault Accessible={health['biometric_storage']['accessible']}")

        # ----------------------------------------------------------------------
        # Step 12: Disposable User Deletion
        # ----------------------------------------------------------------------
        print("\n[Step 19] Testing DELETE /api/v1/admin/users/{id} on disposable account...")
        disp_res = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Disposable Operator",
                "email": disposable_email,
                "password": test_password,
                "password_confirm": test_password,
                "accept_privacy_terms": True,
            },
        )
        assert disp_res.status_code == 201, f"Register disposable failed: {disp_res.text}"
        disp_id = disp_res.json()["data"]["id"]

        del_res = await client.delete(f"/api/v1/admin/users/{disp_id}", headers=admin_headers)
        assert del_res.status_code == 200, f"Delete user failed: {del_res.text}"
        assert del_res.json()["data"]["deleted"] is True
        print(f"  ✓ Disposable user {disp_id} permanently deleted.")

    print("\n" + "=" * 75)
    print("ALL 19 PHASE 8D LIVE HTTP INTEGRATION STEPS PASSED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_phase_8d_live_verification())
