"""Explicit PostgreSQL migrations; credentials come from configuration only."""

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import load_settings
from app.models import Base

settings = load_settings()
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
        connect_args={'connect_timeout': 3},
    )
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
