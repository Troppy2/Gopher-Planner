"""Transaction failure checks in the separate API test database, all rolled back."""

from copy import deepcopy
import json
import os
from pathlib import Path

from dotenv import dotenv_values
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app import create_app

PATH = '/api/v1/dev/student/academic-profile'
pytestmark = pytest.mark.skipif(os.environ.get('RUN_POSTGRES_API_TESTS') != 'true',
                               reason='Requires explicit independent API test database opt-in.')


@pytest.fixture
def api(monkeypatch):
    backend = Path(__file__).resolve().parents[1]
    config = dotenv_values(backend / '.env.api-test')
    url = make_url(config['DATABASE_URL'])
    assert url.host == '127.0.0.1' and url.database.startswith('gopher_api_test_')
    monkeypatch.setenv('DATABASE_URL', config['DATABASE_URL'])
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setenv('ENABLE_DEV_STUDENT_API', 'true')
    engine = create_engine(url)
    app = create_app()
    with engine.connect() as connection:
        outer = connection.begin()
        try:
            app.extensions['database_session_factory'] = sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint')
            client = app.test_client()
            sample = json.loads((backend / 'tests/fixtures/academic_profile.json').read_text())
            assert client.put(PATH, json=sample).status_code == 200
            yield client, connection, sample
        finally:
            outer.rollback()
    app.extensions['database_engine'].dispose()
    engine.dispose()


def test_failure_after_parent_update_and_child_replacement_rolls_back_everything(api):
    client, connection, sample = api
    before = client.get(PATH).json
    changed = deepcopy(sample)
    changed['profile']['max_credits_per_term'] = 12
    changed['course_records'][0]['grade'] = 'B'

    def fail_extra_insert(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.startswith('INSERT INTO extra_credits'):
            raise SQLAlchemyError('Simulated write failure after replacing courses')

    event.listen(connection, 'before_cursor_execute', fail_extra_insert)
    try:
        response = client.put(PATH, json=changed)
        assert response.status_code == 503
        assert 'Simulated' not in response.get_data(as_text=True)
    finally:
        event.remove(connection, 'before_cursor_execute', fail_extra_insert)
    assert client.get(PATH).json == before


def test_empty_arrays_clear_children_and_unknown_grade_stays_unknown(api):
    client, _connection, sample = api
    cleared = deepcopy(sample)
    cleared['course_records'] = []
    cleared['extra_credits'] = []
    assert client.put(PATH, json=cleared).json == cleared
    assert client.get(PATH).json == cleared
    assert client.put(PATH, json=sample).status_code == 200
    row = next(row for row in client.get(PATH).json['course_records'] if row['course_code'] == 'MATH 1272')
    assert row['grade'] is None and row['grading_basis'] is None


@pytest.mark.parametrize(('body', 'content_type', 'status'), [
    ('{"profile":', 'application/json', 400),
    ('{"profile": {}, "profile": {}}', 'application/json', 400),
    ('{"value": NaN}', 'application/json', 400),
    ('{}', 'text/plain', 415),
    ('[]', 'application/json', 422),
    (' ', 'application/json', 400),
])
def test_bad_http_input_preserves_old_snapshot(api, body, content_type, status):
    client, _connection, _sample = api
    before = client.get(PATH).json
    assert client.put(PATH, data=body, content_type=content_type).status_code == status
    assert client.get(PATH).json == before
