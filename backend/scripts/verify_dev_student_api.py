"""Real HTTP acceptance in a NEW isolated PostgreSQL database, never the dev DB.

Run from backend: .venv/bin/python scripts/verify_dev_student_api.py
Leaves its unique database and ignored .env.api-test for the later restart step.
Starts Flask once, stops it on exit, and never performs restart acceptance.
"""

from copy import deepcopy
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, text
from app.core.config import load_settings


def main():
    os.chdir(BACKEND)
    for key in ('DATABASE_URL', 'APP_ENV', 'ENABLE_DEV_STUDENT_API'):
        os.environ.pop(key, None)
    settings = load_settings()
    if settings.app_env != 'development' or settings.database_url.host != '127.0.0.1':
        raise RuntimeError('Requires the explicitly configured local development PostgreSQL.')
    manifest = BACKEND / '.env.api-test'
    if manifest.exists():
        raise RuntimeError('.env.api-test already exists; stopping without overwriting or clearing its database.')
    database = 'gopher_api_test_' + uuid.uuid4().hex[:12]
    test_url = settings.database_url.set(database=database)
    admin = create_engine(settings.database_url.set(database='postgres'), isolation_level='AUTOCOMMIT')
    dev = create_engine(settings.database_url)
    tables = ('student_profiles', 'course_records', 'extra_credits')
    with dev.connect() as connection:
        before = {table: connection.execute(text('SELECT * FROM ' + table + ' ORDER BY id')).all() for table in tables}
    try:
        with admin.connect() as connection:
            # The identifier is generated solely from a fixed prefix and hex UUID.
            connection.exec_driver_sql('CREATE DATABASE "' + database + '"')
    finally:
        admin.dispose()
    fd = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as file:
        file.write('DATABASE_URL=' + test_url.render_as_string(hide_password=False)
                   + '\nAPP_ENV=development\nENABLE_DEV_STUDENT_API=true\n')
    print('Created isolated test database:', database, flush=True)
    env = dict(os.environ, DATABASE_URL=test_url.render_as_string(hide_password=False),
               APP_ENV='development', ENABLE_DEV_STUDENT_API='true')
    migration = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'],
                               env=env, capture_output=True, text=True)
    if migration.returncode:
        raise RuntimeError('Test database migration failed; sensitive diagnostics suppressed.')
    print('Test database migrated to 0002_academic.', flush=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = subprocess.Popen([sys.executable, '-m', 'flask', '--app', 'app:create_app',
                               'run', '--host', '127.0.0.1', '--port', str(port)],
                              env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f'http://127.0.0.1:{port}/api/v1/dev/student/academic-profile'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def http(method, payload=None, raw=None, query=''):
        data = raw if raw is not None else None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(url + query, data=data, method=method,
                                     headers={'Content-Type': 'application/json'})
        try:
            response = opener.open(req, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    test_engine = create_engine(test_url)
    try:
        for _ in range(50):
            if server.poll() is not None:
                raise RuntimeError('Flask exited before acceptance.')
            try:
                status, body = http('GET')
                assert status == 404 and body['error']['code'] == 'not_found'
                break
            except (ConnectionError, urllib.error.URLError):
                time.sleep(.1)
        else:
            raise RuntimeError('Flask readiness timed out.')
        print('Initial GET: 404 passed.', flush=True)
        sample = json.loads((BACKEND / 'tests/fixtures/academic_profile.json').read_text())
        expected = deepcopy(sample)
        expected['course_records'].sort(key=lambda row: row['course_code'])
        status, saved = http('PUT', sample)
        assert status == 200 and saved == expected
        assert http('GET') == (200, expected)
        print('PUT 200 and GET identical snapshot: passed.', flush=True)
        assert http('PUT', sample) == (200, expected)
        with test_engine.connect() as connection:
            counts = tuple(connection.execute(text('SELECT count(*) FROM ' + table)).scalar_one() for table in tables)
            assert counts == (1, 3, 1)
        print('Repeated PUT: counts remain 1 student / 3 courses / 1 extra: passed.', flush=True)
        invalid = deepcopy(sample)
        invalid['profile']['max_credits_per_term'] = 12
        invalid['course_records'][2]['earned_credits'] = 1
        status, body = http('PUT', invalid)
        assert status == 422 and body['error']['details'][0]['field'] == 'course_records[2].earned_credits'
        assert http('GET') == (200, expected)
        print('Invalid PUT 422 with field detail; entire old snapshot unchanged: passed.', flush=True)
        invalid = deepcopy(sample)
        invalid['course_records'][0]['credit_reference'] = 'TEST-IB-001'
        assert http('PUT', invalid)[0] == 422
        assert http('GET') == (200, expected)
        assert http('PUT', sample | {'student_id': 2})[0] == 422
        assert http('GET', query='?student_id=2')[0] == 422
        assert http('PUT', raw=b'{"profile":')[0] == 400
        assert http('GET') == (200, expected)
        print('Cross-table duplication, client identity and malformed JSON rejected: passed.', flush=True)
        replacement = deepcopy(sample)
        replacement['profile']['max_credits_per_term'] = 15
        replacement['course_records'] = [replacement['course_records'][0]]
        replacement['extra_credits'] = []
        assert http('PUT', replacement) == (200, replacement)
        with test_engine.connect() as connection:
            assert tuple(connection.execute(text('SELECT count(*) FROM ' + table)).scalar_one()
                         for table in tables) == (1, 1, 0)
        assert http('PUT', sample) == (200, expected)
        print('Full replacement deletes omitted children; original fictional sample restored: passed.', flush=True)
    finally:
        server.terminate()
        server.wait(timeout=10)
        test_engine.dispose()
        with dev.connect() as connection:
            after = {table: connection.execute(text('SELECT * FROM ' + table + ' ORDER BY id')).all() for table in tables}
            assert after == before, 'Development database was unexpectedly changed.'
        dev.dispose()
        print('Verification Flask stopped; development database rows unchanged.', flush=True)
    print('Independent database and ignored .env.api-test retained for the next step.', flush=True)


if __name__ == '__main__':
    main()
