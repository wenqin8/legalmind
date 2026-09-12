"""Alembic environment backed by the same validated application settings."""

from logging.config import fileConfig
import os

from alembic import context

from app.core.config import get_settings
from app.db import models  # noqa: F401 - registers model metadata
from app.db.base import Base
from app.db.session import Database

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    """Allow CI migration checks to use an isolated database without local .env."""

    override = os.environ.get("ALEMBIC_DATABASE_URL")
    if override:
        return override
    return get_settings().database_url.get_secret_value()


def run_migrations_offline() -> None:
    url = database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database = Database(database_url())
    try:
        with database.engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        database.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
