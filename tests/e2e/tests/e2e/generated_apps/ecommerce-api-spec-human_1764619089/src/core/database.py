"""
Database Configuration and Session Management

Provides async database connection using SQLAlchemy 2.0+ with AsyncEngine.
Uses lazy initialization to avoid engine creation at import time.
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine, AsyncEngine
from sqlalchemy.orm import declarative_base
from src.core.config import get_settings
import structlog

logger = structlog.get_logger(__name__)

# Create declarative base for models
Base = declarative_base()

# Lazy initialization - engine created on first use
_engine: Optional[AsyncEngine] = None
_async_session: Optional[async_sessionmaker] = None


def _get_engine() -> AsyncEngine:
    """
    Get or create the database engine (lazy initialization).

    Bug #30 fix: Engine is created on first access, not at module import.
    This allows tests to override DATABASE_URL before engine creation.

    Bug #77 fix: Added pool_timeout and SQLite-specific connect_args to prevent
    connection pool exhaustion and thread locking issues.

    Returns:
        AsyncEngine: SQLAlchemy async engine
    """
    global _engine
    if _engine is None:
        settings = get_settings()

        # Bug #77: Build engine kwargs with timeout and SQLite support
        engine_kwargs = {
            "echo": settings.db_echo,
            "pool_pre_ping": True,
            "future": True,
            "pool_timeout": 30,  # Bug #77: Don't wait forever for connections
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }

        # Bug #77: SQLite-specific configuration
        # SQLite doesn't support pool_size/max_overflow, needs different config
        if "sqlite" in settings.database_url.lower():
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            # For SQLite, use StaticPool to avoid connection issues
            from sqlalchemy.pool import StaticPool
            engine_kwargs["poolclass"] = StaticPool
        else:
            # PostgreSQL/MySQL configuration
            engine_kwargs["pool_size"] = settings.db_pool_size
            engine_kwargs["max_overflow"] = settings.db_max_overflow

        _engine = create_async_engine(settings.database_url, **engine_kwargs)
        logger.info("database_engine_created", url=settings.database_url[:50] + "[truncated]")
    return _engine


def _get_session_maker() -> async_sessionmaker:
    """
    Get or create the session factory (lazy initialization).

    Returns:
        async_sessionmaker: SQLAlchemy async session factory
    """
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session


# Module-level engine accessor (for compatibility)
# Note: Cannot use @property on module functions - use direct function call
def get_engine() -> AsyncEngine:
    """Get the database engine (lazy initialization)."""
    return _get_engine()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session for request
    """
    session_maker = _get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in models.
    Should only be used for development/testing.
    Use Alembic migrations for production.

    Bug #97 Fix: Import models before create_all to ensure
    they are registered in Base.metadata.

    Bug #99 Fix: Use checkfirst=True to be idempotent - prevents
    "DuplicateTable" errors when alembic also creates tables.
    """
    # Bug #97: Import models to register them in Base.metadata
    # This prevents "relation does not exist" errors when seed_db.py
    # calls init_db() before importing entity classes
    import src.models.entities  # noqa: F401 - Required for create_all

    engine = _get_engine()
    async with engine.begin() as conn:
        # Bug #99: checkfirst=True makes this idempotent
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
        logger.info("Database tables created")


async def close_db() -> None:
    """
    Close database connections.

    Properly disposes of the connection pool.
    """
    global _engine, _async_session
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session = None
        logger.info("Database connections closed")