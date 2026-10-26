"""Infrastructure checks only; these do not stand in for PostgreSQL acceptance."""

import pytest
import psycopg
from sqlalchemy import event

from app import create_app
from app.core.config import load_settings
from app.models import Base


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.setattr('app.core.config.load_dotenv', lambda *args, **kwargs: None)
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://test:test@127.0.0.1:5432/test')
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.delenv('ENABLE_DEV_STUDENT_API', raising=False)


def test_startup_and_liveness_do_not_connect_or_create_tables(monkeypatch):
    # An attempted psycopg connection fails this test, even if swallowed by code.
    attempts = []

    def forbidden_connect(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Startup must not connect to PostgreSQL.')

    monkeypatch.setattr('psycopg.connect', forbidden_connect)
    app = create_app()
    try:
        response = app.test_client().get('/api/v1/health')
        assert response.status_code == 200
        assert response.json == {'status': 'ok'}
        assert attempts == []
        assert set(Base.metadata.tables) == {'student_profiles', 'course_records', 'extra_credits'}
        assert app.config['ENABLE_DEV_STUDENT_API'] is False
        assert app.test_client().get('/api/v1/dev/student/academic-profile').status_code == 404
    finally:
        app.extensions['database_engine'].dispose()


@pytest.mark.parametrize('url', ['', 'not-a-url', 'sqlite:///students.db', 'postgresql://localhost/test'])
def test_reject_missing_or_non_psycopg_database_url(monkeypatch, url):
    monkeypatch.setenv('DATABASE_URL', url)
    with pytest.raises(ValueError):
        load_settings()


@pytest.mark.parametrize('environment', ['testing', 'production'])
def test_dev_switch_cannot_enable_outside_development(monkeypatch, environment):
    monkeypatch.setenv('APP_ENV', environment)
    monkeypatch.setenv('ENABLE_DEV_STUDENT_API', 'true')
    with pytest.raises(ValueError, match='requires APP_ENV=development'):
        load_settings()


def test_dev_switch_rejects_ambiguous_values(monkeypatch):
    monkeypatch.setenv('ENABLE_DEV_STUDENT_API', 'yes')
    with pytest.raises(ValueError, match='true or false'):
        load_settings()


def test_connection_failure_message_does_not_leak_credentials():
    app = create_app()
    engine = app.extensions['database_engine']

    def refuse_connection(*args, **kwargs):
        raise psycopg.OperationalError('secret-connection-details')

    event.listen(engine, 'do_connect', refuse_connection)
    try:
        result = app.test_cli_runner().invoke(args=['check-db'])
        assert result.exit_code != 0
        assert 'PostgreSQL connection failed' in result.output
        assert 'secret-connection-details' not in result.output
    finally:
        engine.dispose()
