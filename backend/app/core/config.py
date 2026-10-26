"""Configuration shared by Flask and Alembic; never print connection URLs."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class Settings:
    database_url: URL
    app_env: str
    enable_dev_student_api: bool


def load_settings() -> Settings:
    # Explicit environment variables take priority over backend/.env.
    load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)
    raw_url = os.environ.get('DATABASE_URL')
    if not raw_url:
        raise ValueError('DATABASE_URL is required.')
    try:
        url = make_url(raw_url)
    except ArgumentError:
        raise ValueError('DATABASE_URL is not a valid SQLAlchemy URL.') from None
    if url.drivername != 'postgresql+psycopg' or not url.host or not url.database:
        raise ValueError('DATABASE_URL must use postgresql+psycopg with a host and database.')

    app_env = os.environ.get('APP_ENV', 'development')
    if app_env not in {'development', 'testing', 'production'}:
        raise ValueError('APP_ENV must be development, testing, or production.')
    flag = os.environ.get('ENABLE_DEV_STUDENT_API', 'false')
    if flag not in {'true', 'false'}:
        raise ValueError('ENABLE_DEV_STUDENT_API must be true or false.')
    enabled = flag == 'true'
    if enabled and app_env != 'development':
        raise ValueError('ENABLE_DEV_STUDENT_API requires APP_ENV=development.')
    return Settings(url, app_env, enabled)
