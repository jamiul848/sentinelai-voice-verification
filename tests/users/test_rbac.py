"""Integration tests for Role-Based Access Control (RBAC) and administrative management."""

import pytest
from httpx import AsyncClient

from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(async_client: AsyncClient):
    """Verify that accessing protected endpoints without a token returns HTTP 401 Unauthorized."""
    res = await async_client.get("/api/v1/users/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_user_forbidden_from_admin_endpoints(async_client: AsyncClient, seeded_user):
    """Verify that a regular USER accessing admin endpoints receives HTTP 403 Forbidden."""
    # Log in as regular user
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@sentinelvoice.io", "password": "ValidPassword123!"},
    )
    user_token = login_res.json()["data"]["access_token"]

    # Attempt to access admin user listing
    res = await async_client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 403
    assert "forbidden" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_can_access_admin_endpoints(
    async_client: AsyncClient,
    seeded_admin,
    seeded_user,
):
    """Verify that an ADMIN can list users, view user details, and modify statuses."""
    # Log in as admin
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinelvoice.io", "password": "AdminSecurePass123!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin lists users
    list_res = await async_client.get("/api/v1/admin/users", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()["data"]) >= 2

    # 2. Admin inspects standard user
    user_id = str(seeded_user.id)
    get_res = await async_client.get(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["email"] == "testuser@sentinelvoice.io"

    # 3. Admin deactivates user
    status_res = await async_client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert status_res.status_code == 200
    assert status_res.json()["data"]["is_active"] is False

    # 4. Admin updates user roles
    roles_res = await async_client.patch(
        f"/api/v1/admin/users/{user_id}/roles",
        json={"roles": ["USER", "ANALYST"]},
        headers=headers,
    )
    assert roles_res.status_code == 200
    assert "ANALYST" in roles_res.json()["data"]["roles"]


@pytest.mark.asyncio
async def test_admin_self_deactivation_prevented(async_client: AsyncClient, seeded_admin):
    """Verify that an administrator cannot deactivate their own account."""
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinelvoice.io", "password": "AdminSecurePass123!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]
    admin_id = str(seeded_admin.id)

    res = await async_client.patch(
        f"/api/v1/admin/users/{admin_id}/status",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "cannot deactivate their own account" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_self_deletion_prevented(async_client: AsyncClient, seeded_admin):
    """Verify that an administrator cannot delete their own account."""
    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinelvoice.io", "password": "AdminSecurePass123!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]
    admin_id = str(seeded_admin.id)

    res = await async_client.delete(
        f"/api/v1/admin/users/{admin_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 400
    assert "cannot delete their own account" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_last_admin_deactivation_prevented(
    async_client: AsyncClient,
    seeded_admin,
    seeded_user,
    test_session,
):
    """Verify that deactivating the only active administrator is blocked."""
    repo = UserRepository(test_session)
    # Promote seeded_user to admin temporarily to make 2 admins
    admin_role = await repo.get_role_by_name("ADMIN")
    await repo.assign_role(seeded_user.id, admin_role.id)
    await test_session.commit()

    admin_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@sentinelvoice.io", "password": "AdminSecurePass123!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Deactivate the second admin (now 1 admin remains)
    r1 = await async_client.patch(
        f"/api/v1/admin/users/{seeded_user.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert r1.status_code == 200

    # Attempting to deactivate seeded_user again when inactive or if someone tries to deactivate the last admin
    # seeded_admin is now the sole active admin. If an admin tries to deactivate seeded_admin:
    r2 = await async_client.patch(
        f"/api/v1/admin/users/{seeded_admin.id}/status",
        json={"is_active": False},
        headers=headers,
    )
    assert r2.status_code == 400

