"""Shared pytest fixtures for Sentinel Voice authentication and API tests."""

from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sentinelai.auth.password import hash_password
from sentinelai.database.connection import get_db_session
from sentinelai.database.models import Base
from sentinelai.database.repositories.user_repository import UserRepository
from sentinelai.main import app


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """Create an isolated in-memory SQLite async database engine for fast API testing."""
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
async def test_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional AsyncSession bound to the in-memory engine."""
    session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an AsyncClient with the database session dependency overridden."""
    async def _override_get_db_session():
        yield test_session

    app.dependency_overrides[get_db_session] = _override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seeded_user(test_session: AsyncSession):
    """Create and seed a standard active USER with known credentials."""
    repo = UserRepository(test_session)
    user_role = await repo.get_role_by_name("USER")
    if not user_role:
        user_role = await repo.create_role(name="USER", description="Standard User")

    pw_hash = hash_password("ValidPassword123!")
    user = await repo.create_user(
        email="testuser@sentinelvoice.io",
        hashed_password=pw_hash,
        full_name="Standard Test User",
        is_active=True,
        is_verified=True,
    )
    await repo.assign_role(user.id, user_role.id)
    await test_session.commit()
    return await repo.get_by_id(user.id)


@pytest_asyncio.fixture(scope="function")
async def seeded_admin(test_session: AsyncSession):
    """Create and seed an active ADMIN user."""
    repo = UserRepository(test_session)
    admin_role = await repo.get_role_by_name("ADMIN")
    if not admin_role:
        admin_role = await repo.create_role(name="ADMIN", description="Administrator")

    pw_hash = hash_password("AdminSecurePass123!")
    admin = await repo.create_user(
        email="admin@sentinelvoice.io",
        hashed_password=pw_hash,
        full_name="System Administrator",
        is_active=True,
        is_verified=True,
    )
    await repo.assign_role(admin.id, admin_role.id)
    await test_session.commit()
    return await repo.get_by_id(admin.id)

