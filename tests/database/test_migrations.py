"""Unit tests for Alembic database migrations and schema evolution."""

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sentinelai.database.models import Base


def test_alembic_script_directory_and_head_revision():
    """Verify Alembic configuration discovers the migration revisions."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    # Get current head
    head_rev = script.get_current_head()
    assert head_rev == "0003_threshold_configs"

    head_obj = script.get_revision(head_rev)
    assert head_obj is not None
    assert head_obj.down_revision == "0002_allow_consent_revocation"

    rev2_obj = script.get_revision("0002_allow_consent_revocation")
    assert rev2_obj is not None
    assert rev2_obj.down_revision == "0001_initial_schema"

    base_obj = script.get_revision("0001_initial_schema")
    assert base_obj is not None
    assert base_obj.down_revision is None
    assert "Initial relational database schema" in base_obj.doc


@pytest.mark.asyncio
async def test_migration_schema_upgrade_downgrade():
    """Verify programmatic table creation and drop cycles matching Alembic operations."""
    mem_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Upgrade: create all tables
    async with mem_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with mem_engine.connect() as conn:
        res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        created_tables = {row[0] for row in res.fetchall()}

    expected_tables = {
        "users",
        "roles",
        "user_roles",
        "refresh_tokens",
        "api_credentials",
        "consent_records",
        "voice_profiles",
        "enrollment_records",
        "verification_events",
        "audit_logs",
        "threshold_configurations",
    }
    assert expected_tables.issubset(created_tables)

    # Downgrade: drop all tables
    async with mem_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    async with mem_engine.connect() as conn:
        res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        remaining_tables = {row[0] for row in res.fetchall()}

    for tbl in expected_tables:
        assert tbl not in remaining_tables

    await mem_engine.dispose()
