import json
from datetime import timedelta
from app.extensions import db


def test_summary_and_status(app, make_user, capsys, tmp_path):
    from app.models import DataReport
    from app.models.user import utc_now
    from scripts.report_summary import main
    alice, bob = make_user(), make_user()
    now = utc_now()
    db.session.add_all([
        DataReport(user_id=alice.id, target_type='course', course_code='TEST 1001', reason='other', note='Synthetic note ' + 'x' * 240, created_at=now - timedelta(hours=2)),
        DataReport(user_id=bob.id, target_type='course', course_code='TEST 1001', reason='details_wrong', created_at=now - timedelta(hours=1)),
        DataReport(user_id=alice.id, target_type='requirement', program_id='synthetic', catalog_term='Fall 2026', requirement_id='core', reason='other', created_at=now),
    ])
    db.session.commit()
    path = tmp_path / 'summary.json'
    assert main(['--json', str(path)], application=app) == 0
    output = capsys.readouterr().out
    assert 'Synthetic note' not in output
    assert alice.email not in output and bob.email not in output
    groups = json.loads(path.read_text())
    assert [g['students'] for g in groups] == [2, 1]
    assert groups[0]['reasons'] == {'other': 1, 'details_wrong': 1}
    assert 'notes' not in groups[0]
    assert 'Fall 2026' in output
    main(['--notes', '--json', str(path)], application=app)
    assert len(json.loads(path.read_text())[0]['notes'][0]) == 200
    report_id = db.session.scalar(db.select(DataReport.id).where(DataReport.target_type == 'requirement'))
    assert main(['--set-status', str(report_id), 'dismissed'], application=app) == 0
    assert db.session.get(DataReport, report_id).status == 'dismissed'
    assert main(['--set-status', '99999', 'open'], application=app) == 1
