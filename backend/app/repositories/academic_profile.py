"""Only the server-selected development student is accessible here."""

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.models import CourseRecord, ExtraCredit, StudentProfile

DEV_STUDENT_ID = 1


def term_columns(prefix, value):
    return {prefix + '_year': None if value is None else value['year'],
            prefix + '_season': None if value is None else value['season']}


def replace_snapshot(session, snapshot):
    profile = {key: value for key, value in snapshot.profile.items()
               if key not in {'current_term', 'target_graduation_term'}}
    profile.update(term_columns('current_term', snapshot.profile['current_term']))
    profile.update(term_columns('target_graduation_term', snapshot.profile['target_graduation_term']))
    # Upsert locks the fixed parent row, including concurrent first saves. All
    # writers acquire that lock before touching children, so snapshots cannot mix.
    statement = insert(StudentProfile).values(id=DEV_STUDENT_ID, **profile)
    session.execute(statement.on_conflict_do_update(index_elements=['id'], set_=profile))
    session.execute(delete(CourseRecord).where(CourseRecord.student_id == DEV_STUDENT_ID))
    session.execute(delete(ExtraCredit).where(ExtraCredit.student_id == DEV_STUDENT_ID))
    courses = []
    for record in snapshot.courses:
        fields = {key: value for key, value in record.items() if key != 'term'}
        fields.update(term_columns('term', record['term']))
        courses.append(fields | {'student_id': DEV_STUDENT_ID})
    if courses:
        session.execute(insert(CourseRecord), courses)
    if snapshot.extra:
        session.execute(insert(ExtraCredit), [row | {'student_id': DEV_STUDENT_ID} for row in snapshot.extra])


def read_snapshot(session):
    # Shared parent lock gives a coherent parent/children snapshot even with
    # PostgreSQL's default READ COMMITTED isolation and concurrent PUT requests.
    student = session.execute(select(StudentProfile).where(StudentProfile.id == DEV_STUDENT_ID)
                              .with_for_update(read=True)).scalar_one_or_none()
    if student is None:
        return None
    courses = session.execute(select(CourseRecord).where(CourseRecord.student_id == DEV_STUDENT_ID)).scalars().all()
    extra = session.execute(select(ExtraCredit).where(ExtraCredit.student_id == DEV_STUDENT_ID)).scalars().all()
    return student, courses, extra
