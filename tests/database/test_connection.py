"""Unit tests for Sentinel Voice database connection management and session lifecycle."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from sentinelai.database.connection import (
    check_database_health,
    close_db,
    get_async_engine,
    get_db_session,
    get_session_factory,
    init_db,
)
from sentinelai.database.exceptions import DatabaseConnectionError


@pytest.mark.asyncio
async def test_async_engine_and_session_factory():
    """Verify AsyncEngine creation, session maker binding, and execution."""
    test_url = "sqlite+aiosqlite:///:memory:"
    engine = get_async_engine(test_url)
    assert isinstance(engine, AsyncEngine)

    session_factory = get_session_factory(engine)
    assert session_factory is not None

    async with session_factory() as session:
        assert isinstance(session, AsyncSession)
        res = await session.execute(text("SELECT 42"))
        assert res.scalar_one() == 42

    await engine.dispose()


@pytest.mark.asyncio
async def test_database_health_check_healthy(async_db_engine):
    """Verify health check returns True on accessible engine."""
    healthy = await check_database_health(async_db_engine)
    assert healthy is True


@pytest.mark.asyncio
async def test_database_health_check_unhealthy():
    """Verify health check returns False when database is unreachable."""
    # Use an invalid engine whose connection fails
    bad_engine = create_async_engine("sqlite+aiosqlite:///nonexistent_dir/bad_db.db")
    healthy = await check_database_health(bad_engine)
    assert healthy is False
    await bad_engine.dispose()


@pytest.mark.asyncio
async def test_engine_disposal_lifecycle():
    """Verify close_db properly disposes global singletons without errors."""
    await close_db()
    # Should be idempotent
    await close_db()


@pytest.mark.asyncio
async def test_init_db_creates_all_tables():
    """Verify init_db initializes the full schema on an empty database."""
    mem_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(mem_engine)

    async with mem_engine.connect() as conn:
        res = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in res.fetchall()]
        assert "users" in tables
        assert "roles" in tables
        assert "voice_profiles" in tables
        assert "verification_events" in tables

    await mem_engine.dispose()

