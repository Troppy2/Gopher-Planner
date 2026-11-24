"""Report contracts use invented accounts, catalog rows, and program fixtures only."""
from datetime import timedelta

import pytest
from sqlalchemy import delete, select

from app.extensions import db


@pytest.fixture(autouse=True)
def synthetic_programs(program_files):
    pass


def course(**extra):
    return dict(targetType="course", courseCode="CSCI 1001", reason="other", **extra)


def test_course_create_and_duplicate_update(client, make_user, login_as, post_headers, catalog):
    login_as(make_user())
    first = client.post('/api/v1/reports', json=course(note='  Synthetic issue  '), headers=post_headers)
    assert first.status_code == 201
    assert first.json['note'] == 'Synthetic issue'
    second = client.post('/api/v1/reports', json=course(note=' '), headers=post_headers)
    assert second.status_code == 200
    assert second.json['id'] == first.json['id']
    assert second.json['note'] is None
    assert len(client.get('/api/v1/reports').json['reports']) == 1
    assert set(second.json) == {'id', 'targetType', 'courseCode', 'requirementId', 'reason', 'note', 'status', 'createdAt', 'updatedAt'}


def test_requirement_resolves_context(client, make_user, login_as, post_headers):
    from app.models import Plan, DataReport
    user = make_user()
    user.major = 'Synthetic B.S.'
    db.session.add(Plan(user_id=user.id, catalog_term='Fall 2026'))
    db.session.commit()
    login_as(user)
    body = dict(targetType='requirement', requirementId='core', reason='missing_course')
    result = client.post('/api/v1/reports', json=body, headers=post_headers)
    assert result.status_code == 201
    report = db.session.get(DataReport, result.json['id'])
    assert (report.program_id, report.catalog_term) == ('synthetic', 'Fall 2026')
    assert client.post('/api/v1/reports', json=body, headers=post_headers).status_code == 200
    for fields in ({'programId': 'synthetic'}, {'catalogTerm': 'Fall 2026'}, {'requirementId': 'intro'}):
        response = client.post('/api/v1/reports', json={**body, **fields}, headers=post_headers)
        assert response.status_code == 400
        assert response.json['code'] == 'invalid_report'
    assert client.post('/api/v1/reports', json=dict(targetType='course', courseCode='TEST 1001', reason='other'), headers=post_headers).status_code == 201


@pytest.mark.parametrize('patch', [
    {'reason': 'unknown'}, {'reason': 'missing_course'}, {'reason': []},
    {'courseCode': 'ZZZZ 9999'}, {'courseCode': 1}, {'targetType': []},
    {'note': 'x' * 501}, {'note': 42}, {'note': None}, {'userId': 2},
    {'program_id': 'synthetic'}, {'requirementId': 'core'},
])
def test_validation(patch, client, make_user, login_as, post_headers, catalog):
    login_as(make_user())
    response = client.post('/api/v1/reports', json={**course(), **patch}, headers=post_headers)
    assert response.status_code == 400
    assert response.json['code'] == 'invalid_report'


def test_auth_origin_and_unconfirmed(client, make_user, login_as, post_headers):
    assert client.get('/api/v1/reports').status_code == 401
    assert client.post('/api/v1/reports', json=course(), headers=post_headers).status_code == 401
    user = make_user()
    user.major = 'Synthetic B.S.'
    db.session.commit()
    login_as(user)
    assert client.post('/api/v1/reports', json=course(), headers={'Origin': 'https://example.invalid'}).status_code == 403
    result = client.post('/api/v1/reports', json=dict(targetType='requirement', requirementId='core', reason='other'), headers=post_headers)
    assert result.status_code == 400
    assert result.json['code'] == 'program_version_unconfirmed'


def test_rate_limit_boundary_and_updates(client, make_user, login_as, post_headers, catalog):
    from app.models import DataReport
    from app.models.user import utc_now
    user = make_user()
    login_as(user)
    for i in range(19):
        db.session.add(DataReport(user_id=user.id, target_type='course', course_code=f'TEST {1000+i}', reason='other', status='resolved'))
    db.session.commit()
    response = client.post('/api/v1/reports', json=course(), headers=post_headers)
    assert response.status_code == 201  # twentieth new report
    assert client.post('/api/v1/reports', json=course(note='Update at limit'), headers=post_headers).status_code == 200
    response = client.post('/api/v1/reports', json={**course(), 'courseCode': 'CSCI 1002'}, headers=post_headers)
    assert response.status_code == 429
    assert response.json['code'] == 'report_limit'
    row = db.session.scalar(select(DataReport).where(DataReport.status == 'resolved'))
    row.created_at = utc_now() - timedelta(hours=24, seconds=1)
    db.session.commit()
    assert client.post('/api/v1/reports', json={**course(), 'courseCode': 'CSCI 1002'}, headers=post_headers).status_code == 201


def test_ownership_open_filter_and_cascade(client, make_user, login_as, post_headers, catalog):
    from app.models import DataReport, User
    from app.services.reports import get_reports
    alice, bob = make_user(), make_user()
    login_as(alice)
    a = client.post('/api/v1/reports', json=course(), headers=post_headers).json
    login_as(bob)
    b = client.post('/api/v1/reports', json=course(), headers=post_headers)
    assert b.status_code == 201
    assert b.json['id'] != a['id']
    assert [r['id'] for r in client.get('/api/v1/reports?user_id=1').json['reports']] == [b.json['id']]
    assert [r.id for r in get_reports(alice.id)] == [a['id']]
    report = db.session.get(DataReport, b.json['id'])
    report.status = 'resolved'
    db.session.commit()
    assert client.get('/api/v1/reports').json == {'reports': []}
    db.session.execute(delete(User).where(User.id == alice.id))
    db.session.commit()
    assert db.session.get(DataReport, a['id']) is None


def test_database_error_does_not_log_notes(client, make_user, login_as, post_headers, catalog, monkeypatch, caplog):
    from sqlalchemy.exc import StatementError
    from app.services import reports
    login_as(make_user())
    def fail(*args):
        raise StatementError('Synthetic failure', 'INSERT INTO data_reports', {'note': 'PRIVATE_SENTINEL'}, Exception('Synthetic'))
    monkeypatch.setattr(reports, 'create_report', fail)
    response = client.post('/api/v1/reports', json=course(note='PRIVATE_SENTINEL'), headers=post_headers)
    assert response.status_code == 503
    assert 'PRIVATE_SENTINEL' not in caplog.text
