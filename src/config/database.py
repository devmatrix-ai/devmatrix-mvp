"""
Database Configuration

PostgreSQL connection and session management.
"""

import logging
from typing import Generator, AsyncGenerator
from contextlib import contextmanager, asynccontextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# For testing
TEST_DATABASE_URL = "sqlite:///:memory:"


class DatabaseConfig:
    """Database configuration singleton"""

    _engine = None
    _session_factory = None
    _async_engine = None
    _async_session_factory = None
    _base = None

    @classmethod
    def get_engine(cls, url: str = None, echo: bool = False):
        """
        Get SQLAlchemy engine (singleton).

        Args:
            url: Database URL (if None, loads from settings)
            echo: Echo SQL statements

        Returns:
            SQLAlchemy engine
        """
        if cls._engine is None:
            # Load DATABASE_URL from settings if not provided
            if url is None:
                from src.config.settings import get_settings
                settings = get_settings()
                url = settings.DATABASE_URL

            # PostgreSQL engine config
            if url.startswith(("postgresql", "postgres")):
                cls._engine = create_engine(
                    url,
                    echo=echo,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,  # Verify connections
                    pool_recycle=3600,  # Recycle after 1h
                )
            # SQLite for testing
            else:
                cls._engine = create_engine(
                    url,
                    echo=echo,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                )

            logger.info(f"Database engine created: {url.split('@')[-1] if '@' in url else 'test-db'}")  # Hide password

        return cls._engine

    @classmethod
    def get_session_factory(cls):
        """
        Get session factory (singleton).

        Returns:
            SQLAlchemy session factory
        """
        if cls._session_factory is None:
            engine = cls.get_engine()
            cls._session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
            logger.info("Session factory created")

        return cls._session_factory

    @classmethod
    def get_async_engine(cls, url: str = None, echo: bool = False):
        """
        Get async SQLAlchemy engine (singleton).

        Args:
            url: Database URL (if None, loads from settings)
            echo: Echo SQL statements

        Returns:
            Async SQLAlchemy engine
        """
        if cls._async_engine is None:
            # Load DATABASE_URL from settings if not provided
            if url is None:
                from src.config.settings import get_settings
                settings = get_settings()
                url = settings.DATABASE_URL

            # Convert postgresql:// to postgresql+asyncpg://
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)

            # PostgreSQL async engine config
            if "postgresql+asyncpg" in url:
                cls._async_engine = create_async_engine(
                    url,
                    echo=echo,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                )
            # SQLite async for testing
            else:
                # For testing, use aiosqlite
                if url.startswith("sqlite"):
                    url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
                cls._async_engine = create_async_engine(
                    url,
                    echo=echo,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                )

            logger.info(f"Async database engine created: {url.split('@')[-1] if '@' in url else 'test-db'}")

        return cls._async_engine

    @classmethod
    def get_async_session_factory(cls):
        """
        Get async session factory (singleton).

        Returns:
            Async SQLAlchemy session factory
        """
        if cls._async_session_factory is None:
            async_engine = cls.get_async_engine()
            cls._async_session_factory = async_sessionmaker(
                bind=async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
            logger.info("Async session factory created")

        return cls._async_session_factory

    @classmethod
    def get_base(cls):
        """
        Get declarative base (singleton).

        Returns:
            SQLAlchemy declarative base
        """
        if cls._base is None:
            cls._base = declarative_base()
            logger.info("Declarative base created")

        return cls._base

    @classmethod
    def create_all(cls):
        """Create all tables (for testing/development)"""
        engine = cls.get_engine()
        base = cls.get_base()
        base.metadata.create_all(bind=engine)
        logger.info("All tables created")

    @classmethod
    def drop_all(cls):
        """Drop all tables (for testing)"""
        engine = cls.get_engine()
        base = cls.get_base()
        base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")


# Declarative base for models
Base = DatabaseConfig.get_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            items = db.query(Item).all()
            return items
    """
    SessionLocal = DatabaseConfig.get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database session.

    Usage:
        with get_db_context() as db:
            item = db.query(Item).first()
    """
    SessionLocal = DatabaseConfig.get_session_factory()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database session.

    Usage:
        async with get_async_db_context() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()
    """
    AsyncSessionLocal = DatabaseConfig.get_async_session_factory()
    async_db = AsyncSessionLocal()
    try:
        yield async_db
        await async_db.commit()
    except Exception:
        await async_db.rollback()
        raise
    finally:
        await async_db.close()


def init_db():
    """
    Initialize database (create tables if not exist).

    Call this on application startup.
    """
    logger.info("Initializing database...")

    # Import all models to register them
    import src.models.masterplan  # noqa
    import src.models.user  # noqa
    import src.models.user_quota  # noqa
    import src.models.user_usage  # noqa
    import src.models.conversation  # noqa
    import src.models.message  # noqa

    # Create tables
    DatabaseConfig.create_all()

    logger.info("Database initialization complete")
