"""Engine creation is lazy: it does not connect or change database structure."""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import sessionmaker


def init_database(app, database_url: URL) -> None:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={'connect_timeout': 3},
        echo=False,
    )
    app.extensions['database_engine'] = engine
    app.extensions['database_session_factory'] = sessionmaker(
        bind=engine, expire_on_commit=False
    )


def check_database(engine: Engine) -> None:
    """Read-only connectivity and minimum-version check."""
    with engine.connect() as connection:
        connection.execute(text('SELECT 1')).scalar_one()
        version = int(connection.execute(text('SHOW server_version_num')).scalar_one())
        if version < 150000:
            raise ValueError('PostgreSQL 15 or newer is required.')
