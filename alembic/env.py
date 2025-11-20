"""
Alembic environment configuration for async SQLAlchemy.

Supports both sync (legacy) and async (production-ready) database configurations.
Uses asyncio for async migrations when async engine is available.
"""
import asyncio
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import database configuration and models
# Try production-ready async config first, fallback to legacy sync
try:
    from src.core.database import Base
    from src.core.config import get_settings
    settings = get_settings()
    DATABASE_URL = settings.database_url
    USE_ASYNC = DATABASE_URL.startswith("postgresql+asyncpg://")
except ImportError:
    # Fallback to legacy config for backward compatibility
    try:
        from src.config.database import Base
        import os
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://devmatrix:devmatrix@localhost:5432/devmatrix")
        USE_ASYNC = False
    except ImportError:
        # Last resort: create Base directly
        from sqlalchemy.orm import declarative_base
        Base = declarative_base()
        import os
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://devmatrix:devmatrix@localhost:5432/devmatrix")
        USE_ASYNC = False

# Import ALL models to register them with Base.metadata
try:
    import src.models.user  # noqa - Register User model
    import src.models.user_quota  # noqa - Register UserQuota model
    import src.models.user_usage  # noqa - Register UserUsage model
    import src.models.conversation  # noqa - Register Conversation model
    import src.models.message  # noqa - Register Message model
    import src.models.masterplan  # noqa - Register MasterPlan models
    import src.models.audit_log  # noqa - Register AuditLog model
except ImportError:
    pass  # Models not yet created for production-ready setup

# Production-ready models (when they exist)
try:
    import src.models.entities  # noqa - Register production-ready entities
except ImportError:
    pass

# Alembic Config object
config = context.config

# Set sqlalchemy.url from environment
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the provided connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_sync_migrations() -> None:
    """
    Run migrations in 'online' mode with sync engine (legacy).

    Maintained for backward compatibility with existing migrations.
    """
    from sqlalchemy import engine_from_config

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Automatically detects async vs sync database URL and uses appropriate method.
    """
    if USE_ASYNC:
        # Use async migrations for production-ready async database
        asyncio.run(run_async_migrations())
    else:
        # Use sync migrations for legacy database
        run_sync_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
