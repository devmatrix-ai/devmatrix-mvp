"""Alembic environment configuration."""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import database configuration and models
from src.config.database import Base
import os

# Get DATABASE_URL from environment directly (avoid Settings validation for JWT_SECRET)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://devmatrix:devmatrix@localhost:5432/devmatrix")

# Import ALL models to register them with Base.metadata
import src.models.user  # noqa - Register User model
import src.models.user_quota  # noqa - Register UserQuota model
import src.models.user_usage  # noqa - Register UserUsage model
import src.models.conversation  # noqa - Register Conversation model
import src.models.message  # noqa - Register Message model
import src.models.masterplan  # noqa - Register MasterPlan models
import src.models.audit_log  # noqa - Register AuditLog model

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
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
