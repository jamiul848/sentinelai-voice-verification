"""Unit tests for Sentinel Voice UserRepository."""

from datetime import datetime, timedelta, timezone
import uuid

import pytest

from sentinelai.database.exceptions import DuplicateEntityError
from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_and_fetch_user(db_session):
    """Test user creation and case-insensitive email retrieval."""
    repo = UserRepository(db_session)

    user = await repo.create_user(
        email="Scientist@Domain.Org",
        hashed_password="argon2id_mock_hash_value",
        full_name="Chief Scientist",
    )
    assert user.id is not None
    assert user.email == "scientist@domain.org"
    assert user.is_active is True

    # Case-insensitive query
    fetched = await repo.get_by_email("SCIENTIST@DOMAIN.ORG")
    assert fetched is not None
    assert fetched.id == user.id

    # Fetch by primary key
    by_id = await repo.get_by_id(user.id)
    assert by_id is not None
    assert by_id.id == user.id


@pytest.mark.asyncio
async def test_duplicate_email_raises_duplicate_entity_error(db_session):
    """Test creating duplicate email raises custom DuplicateEntityError."""
    repo = UserRepository(db_session)

    await repo.create_user(
        email="unique@domain.com",
        hashed_password="hash",
        full_name="First User",
    )

    with pytest.raises(DuplicateEntityError) as exc_info:
        await repo.create_user(
            email="UNIQUE@DOMAIN.COM",
            hashed_password="hash",
            full_name="Second User",
        )
    assert exc_info.value.entity_name == "User"


@pytest.mark.asyncio
async def test_list_users_pagination(db_session):
    """Test user pagination with skip and limit."""
    repo = UserRepository(db_session)

    for i in range(5):
        await repo.create_user(
            email=f"user_{i}@example.com",
            hashed_password="pw",
            full_name=f"User {i}",
        )

    # First page
    page1 = await repo.list_users(skip=0, limit=3)
    assert len(page1) == 3

    # Second page
    page2 = await repo.list_users(skip=3, limit=3)
    assert len(page2) == 2

    # Total count
    total = await repo.count()
    assert total == 5


@pytest.mark.asyncio
async def test_update_and_deactivate_user(db_session):
    """Test updating user attributes and soft deactivation."""
    repo = UserRepository(db_session)

    user = await repo.create_user(
        email="active_user@example.com",
        hashed_password="pw",
        full_name="Active Name",
    )

    # Update full_name
    updated = await repo.update_user(user.id, full_name="Updated Name")
    assert updated is not None
    assert updated.full_name == "Updated Name"

    # Deactivate
    deactivated = await repo.deactivate_user(user.id)
    assert deactivated is not None
    assert deactivated.is_active is False

    # Verify active_only filter excludes deactivated user
    active_users = await repo.list_users(active_only=True)
    assert user.id not in [u.id for u in active_users]


@pytest.mark.asyncio
async def test_user_roles_management(db_session):
    """Test role assignment, duplicate rejection, and role revocation."""
    repo = UserRepository(db_session)

    user = await repo.create_user(
        email="rbac_user@test.com",
        hashed_password="pw",
        full_name="RBAC User",
    )
    role = await repo.create_role(
        name="SECURITY_AUDITOR",
        description="Audits security logs",
        permissions=["audit:read"],
    )

    # Assign role
    assignment = await repo.assign_role(user.id, role.id)
    assert assignment.user_id == user.id

    # Verify user roles loaded
    user_with_role = await repo.get_by_id(user.id)
    role_names = [r.name for r in user_with_role.roles]
    assert "SECURITY_AUDITOR" in role_names

    # Duplicate assignment should raise DuplicateEntityError
    with pytest.raises(DuplicateEntityError):
        await repo.assign_role(user.id, role.id)

    # Remove role
    removed = await repo.remove_role(user.id, role.id)
    assert removed is True
    user_after_removal = await repo.get_by_id(user.id)
    assert "SECURITY_AUDITOR" not in [r.name for r in user_after_removal.roles]


@pytest.mark.asyncio
async def test_refresh_token_and_api_credentials(db_session):
    """Test refresh token issuance, revocation, and API credential creation."""
    repo = UserRepository(db_session)

    user = await repo.create_user(
        email="token_user@test.com",
        hashed_password="pw",
        full_name="Token User",
    )

    # Issue token
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    token = await repo.create_refresh_token(
        user_id=user.id,
        token_hash="sample_token_hash_value_12345",
        expires_at=expires_at,
    )
    assert token.is_revoked is False

    # Revoke token
    revoked = await repo.revoke_refresh_token("sample_token_hash_value_12345")
    assert revoked is True

    # Create API Credential
    cred = await repo.create_api_credential(
        user_id=user.id,
        name="Mobile App Client",
        key_prefix="sv_live_test",
        key_hash="sample_key_hash_67890",
        scopes=["verify"],
    )
    assert cred.name == "Mobile App Client"
    assert cred.is_active is True

