from sqlalchemy import delete, select

from app.extensions import db
from app.models import Coursework
from app.schemas.coursework import validate_coursework
from app.repositories.locks import lock_user


def serialize_coursework(row):
    return {
        "code": row.code, "title": row.title, "credits": float(row.credits),
        "status": row.status, "term": row.term, "grade": row.grade, "source": row.source,
    }


def get_coursework(user):
    rows = db.session.scalars(select(Coursework).where(Coursework.user_id == user.id).order_by(Coursework.code, Coursework.term)).all()
    return {"courses": [serialize_coursework(row) for row in rows], "skipped": user.coursework_skipped}


def save_coursework(user, body):
    body = validate_coursework(body)
    lock_user(user.id)
    existing = {
        (row.code, row.term): (row.source, row.transcript_id)
        for row in db.session.scalars(select(Coursework).where(Coursework.user_id == user.id))
    }
    user.coursework_skipped = body["skipped"]
    db.session.execute(delete(Coursework).where(Coursework.user_id == user.id))
    for course in body["courses"]:
        values = {key: course.get(key) for key in ("code", "title", "credits", "status", "term", "grade")}
        source, transcript_id = existing.get((values["code"], values["term"]), ("manual", None))
        db.session.add(Coursework(user_id=user.id, source=source, transcript_id=transcript_id, **values))
    db.session.commit()
    return get_coursework(user)
