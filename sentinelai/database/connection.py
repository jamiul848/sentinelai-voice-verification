"""Sentinel Voice - Async Database Connection & Session Management.

Provides asynchronous engine initialization, connection pooling, session factory creation,
FastAPI dependency injection, and health check utilities.

INVARIANT: Database credentials are never printed or leaked in application logs.
"""

from collections.abc import AsyncGenerator
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sentinelai.config import get_settings
from sentinelai.database.base import Base
from sentinelai.database.exceptions import DatabaseConnectionError

logger = logging.getLogger(__name__)

# Module-level singletons
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine(database_url: Optional[str] = None) -> AsyncEngine:
    """Get or create the global AsyncEngine instance.

    Configures connection pooling and dialect-specific options.

    Args:
        database_url: Optional explicit connection string. If omitted,
            settings.database_url is used.

    Returns:
        Configured AsyncEngine instance.

    Raises:
        DatabaseConnectionError: If engine creation fails.
    """
    global _engine
    if _engine is not None and database_url is None:
        return _engine

    settings = get_settings()
    url = database_url or settings.database_url

    engine_kwargs = {
        "echo": settings.database_echo,
        "future": True,
    }

    # SQLite does not support pool_size, max_overflow, or connection timeout
    if "sqlite" in url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_size"] = settings.database_pool_size
        engine_kwargs["max_overflow"] = settings.database_max_overflow
        engine_kwargs["pool_pre_ping"] = settings.database_pool_pre_ping
        engine_kwargs["pool_recycle"] = settings.database_pool_recycle
        engine_kwargs["connect_args"] = {"timeout": settings.database_connect_timeout}

    try:
        engine = create_async_engine(url, **engine_kwargs)
        if database_url is None:
            _engine = engine
        return engine
    except Exception as err:
        # Sanitize exception message to avoid logging raw credentials
        logger.error("Failed to initialize database engine: %s", type(err).__name__)
        raise DatabaseConnectionError("Failed to initialize database engine.") from None


def get_session_factory(
    engine: Optional[AsyncEngine] = None,
) -> async_sessionmaker[AsyncSession]:
    """Get or create the global async session factory.

    Args:
        engine: Optional explicit AsyncEngine. If omitted, global engine is used.

    Returns:
        async_sessionmaker configured with expire_on_commit=False.
    """
    global _session_factory
    if _session_factory is not None and engine is None:
        return _session_factory

    target_engine = engine or get_async_engine()
    factory = async_sessionmaker(
        bind=target_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    if engine is None:
        _session_factory = factory

    return factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding an async database session per request.

    Yields:
        AsyncSession instance committed or rolled back automatically.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db(engine: Optional[AsyncEngine] = None) -> None:
    """Create all database tables defined in Base metadata.

    Primarily used for testing suites and automated bootstrapping.

    Args:
        engine: Optional target AsyncEngine.
    """
    target_engine = engine or get_async_engine()
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_database_health(engine: Optional[AsyncEngine] = None) -> bool:
    """Execute a simple query to verify database connectivity.

    Args:
        engine: Optional target AsyncEngine.

    Returns:
        True if the database responds, False otherwise.
    """
    try:
        target_engine = engine or get_async_engine()
        async with target_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as err:
        logger.warning("Database health check failed: %s", type(err).__name__)
        return False


async def close_db() -> None:
    """Dispose of the global AsyncEngine and clear session factory."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _session_factory = None
