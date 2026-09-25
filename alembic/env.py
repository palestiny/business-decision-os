import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from decision_os.infrastructure.persistence.base import Base
from decision_os.infrastructure.persistence import models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = os.getenv("SQLALCHEMY_DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = os.getenv("SQLALCHEMY_DATABASE_URL", configuration["sqlalchemy.url"])
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
