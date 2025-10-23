"""
Database Configuration

PostgreSQL connection and session management.
"""

import os
import logging
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "devmatrix")
POSTGRES_USER = os.getenv("POSTGRES_USER", "devmatrix")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "devmatrix")

# Build connection URL
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# For testing
TEST_DATABASE_URL = "sqlite:///:memory:"


class DatabaseConfig:
    """Database configuration singleton"""

    _engine = None
    _session_factory = None
    _base = None

    @classmethod
    def get_engine(cls, url: str = DATABASE_URL, echo: bool = False):
        """
        Get SQLAlchemy engine (singleton).

        Args:
            url: Database URL
            echo: Echo SQL statements

        Returns:
            SQLAlchemy engine
        """
        if cls._engine is None:
            # PostgreSQL engine config
            if url.startswith("postgresql"):
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

            logger.info(f"Database engine created: {url.split('@')[-1]}")  # Hide password

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


# Enable SQLAlchemy query logging for development
if os.getenv("ENV") == "development":
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
