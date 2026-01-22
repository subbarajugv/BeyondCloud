"""
Alembic environment configuration for async PostgreSQL migrations.
Uses the same database connection as the main application.
"""
import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add app directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get database URL from our application settings
settings = get_settings()
database_url = settings.database_url

# Override sqlalchemy.url with actual value from environment
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models for autogenerate support
# This allows: alembic revision --autogenerate -m "description"
from app.models import Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, generating SQL without connecting.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        include_object=include_object,
        include_name=include_name,
        compare_type=False,  # Skip type differences (e.g., VARCHAR length)
        compare_server_default=False,  # Skip server default comparisons
    )

    with context.begin_transaction():
        context.run_migrations()


# Tables managed by Node.js/TypeORM - exclude from Python migrations
NODEJS_TABLES = {
    "users", "conversations", "messages", "user_settings",
    "agent_sessions", "refresh_tokens", "password_resets",
    "migrations",  # TypeORM migrations table
}


def include_name(name, type_, parent_names):
    """
    Early filter to exclude Node.js tables during schema reflection.
    This runs before include_object and prevents FK resolution errors.
    """
    if type_ == "table" and name in NODEJS_TABLES:
        return False
    return True


def include_object(obj, name, type_, reflected, compare_to):
    """
    Filter to exclude Node.js managed tables from autogenerate.
    Only Python-managed tables (defined in models.py) are tracked.
    """
    if type_ == "table" and name in NODEJS_TABLES:
        return False
    # Also exclude indexes on Node.js tables
    if type_ == "index" and hasattr(obj, "table") and obj.table.name in NODEJS_TABLES:
        return False
    # Exclude foreign keys that reference Node.js tables
    if type_ == "foreign_key_constraint":
        # obj is a ForeignKeyConstraint - check if it references an excluded table
        if hasattr(obj, "referred_table") and obj.referred_table.name in NODEJS_TABLES:
            return False
        # For reflected FKs, check elements
        if hasattr(obj, "elements"):
            for elem in obj.elements:
                if hasattr(elem, "column") and hasattr(elem.column, "table"):
                    if elem.column.table.name in NODEJS_TABLES:
                        return False
    return True


async def run_async_migrations() -> None:
    """Run migrations with an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
