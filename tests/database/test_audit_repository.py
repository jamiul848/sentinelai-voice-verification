"""Unit tests for Sentinel Voice AuditRepository."""

import uuid

import pytest

from sentinelai.database.repositories.audit_repository import AuditRepository
from sentinelai.database.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_create_and_retrieve_audit_events(db_session):
    """Test creating audit events and retrieving full chronological history."""
    user_repo = UserRepository(db_session)
    audit_repo = AuditRepository(db_session)

    admin = await user_repo.create_user(
        email="admin_actor@sentinel.org",
        hashed_password="pw",
        full_name="Admin Actor",
    )

    # Log 3 events
    e1 = await audit_repo.create_audit_event(
        action="USER_ROLE_ASSIGNED",
        resource_type="user",
        resource_id=str(admin.id),
        actor_user_id=admin.id,
        changes={"role": "ADMIN"},
    )
    e2 = await audit_repo.create_audit_event(
        action="PROFILE_ENROLLMENT_STARTED",
        resource_type="voice_profile",
        resource_id=str(uuid.uuid4()),
        actor_user_id=admin.id,
    )
    e3 = await audit_repo.create_audit_event(
        action="SYSTEM_PARAMETER_CHANGED",
        resource_type="system",
        resource_id="threshold_config",
        actor_user_id=None,  # System action
    )

    assert e1.id is not None
    assert e2.id is not None
    assert e3.id is not None

    # Get audit history for admin
    admin_history = await audit_repo.get_audit_history(actor_user_id=admin.id)
    assert len(admin_history) == 2

    # Get full audit history (all actors)
    all_history = await audit_repo.get_audit_history()
    assert len(all_history) == 3


@pytest.mark.asyncio
async def test_list_resource_events(db_session):
    """Test filtering audit logs by specific resource type and identifier."""
    audit_repo = AuditRepository(db_session)
    profile_id = str(uuid.uuid4())

    await audit_repo.create_audit_event(
        action="PROFILE_CREATED",
        resource_type="voice_profile",
        resource_id=profile_id,
        changes={"status": "ACTIVE"},
    )
    await audit_repo.create_audit_event(
        action="PROFILE_REVOKED",
        resource_type="voice_profile",
        resource_id=profile_id,
        changes={"status": "REVOKED"},
    )
    # Different resource
    await audit_repo.create_audit_event(
        action="USER_DEACTIVATED",
        resource_type="user",
        resource_id=str(uuid.uuid4()),
    )

    resource_events = await audit_repo.list_resource_events(
        resource_type="voice_profile",
        resource_id=profile_id,
    )
    assert len(resource_events) == 2
    actions = [ev.action for ev in resource_events]
    assert "PROFILE_CREATED" in actions
    assert "PROFILE_REVOKED" in actions

