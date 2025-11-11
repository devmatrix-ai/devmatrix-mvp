"""
Core Dependencies

Provides FastAPI dependency injection functions for database sessions and other shared resources.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import DatabaseConfig


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database sessions.

    Yields:
        AsyncSession: Async SQLAlchemy session

    Usage:
        @app.get("/endpoint")
        async def my_endpoint(db: AsyncSession = Depends(get_db_session)):
            # Use db session
            pass
    """
    async_session_factory = DatabaseConfig.get_async_session_factory()

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
