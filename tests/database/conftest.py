"""Pytest fixtures for Sentinel Voice database test suites."""

import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sentinelai.config import get_settings
from sentinelai.database.models import Base


@pytest_asyncio.fixture(scope="function")
async def async_db_engine():
    """Create an isolated in-memory SQLite async engine with all 10 tables initialized.

    Note: This is used for fast, self-contained unit and repository testing.
    Integration tests against a live PostgreSQL instance are explicitly demarcated.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_db_engine):
    """Yield an independent async session for a single unit test with automatic rollback."""
    session_factory = async_sessionmaker(
        bind=async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
