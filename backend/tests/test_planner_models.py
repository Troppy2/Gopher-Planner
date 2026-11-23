from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete
from sqlalchemy import inspect, text
from flask_migrate import downgrade, upgrade

from app import models
from app.extensions import db


@pytest.mark.parametrize("model_name", ["Transcript", "Coursework", "Plan", "PlanCourse"])
def test_planner_model_can_be_inserted_into_migrated_database(app, make_user, model_name):
    assert hasattr(models, model_name), f"Missing {model_name} model"
    user = make_user()
    if model_name == "Transcript":
        row = models.Transcript(id=uuid4().hex, user_id=user.id, file_name="synthetic.pdf", status="parsed")
    elif model_name == "Coursework":
        row = models.Coursework(user_id=user.id, code="CSCI 1001", title="Synthetic course",
                                credits=Decimal("3.5"), status="done", term=None,
                                grade=None, source="manual", transcript_id=None)
    elif model_name == "Plan":
        row = models.Plan(user_id=user.id)
    else:
        assert hasattr(models, "Plan"), "Missing Plan model"
        plan = models.Plan(user_id=user.id)
        db.session.add(plan)
        db.session.flush()
        row = models.PlanCourse(plan_id=plan.id, code="CSCI 1001", term="Spring 2027", source="user")
    db.session.add(row)
    db.session.commit()
    identifier = row.id
    db.session.expire_all()
    loaded = db.session.get(getattr(models, model_name), identifier)
    assert loaded is not None
    if model_name in {"Transcript", "Coursework", "Plan"}:
        assert loaded.created_at is not None
    if model_name in {"Coursework", "Plan"}:
        assert loaded.updated_at is not None
    if model_name == "Coursework":
        assert loaded.credits == Decimal("3.5")


@pytest.mark.parametrize("model_name", ["Plan", "Coursework", "PlanCourse"])
def test_planner_model_rejects_duplicate_identity(app, make_user, model_name):
    user = make_user()
    if model_name == "Plan":
        values = {"user_id": user.id}
    elif model_name == "Coursework":
        values = dict(user_id=user.id, code="CSCI 1001", title="Synthetic course",
                      credits=3, status="done", term="Fall 2025", source="manual")
    else:
        plan = models.Plan(user_id=user.id)
        db.session.add(plan)
        db.session.flush()
        values = dict(plan_id=plan.id, code="CSCI 1001", term="Spring 2027", source="user")
    cls = getattr(models, model_name)
    db.session.add(cls(**values))
    db.session.commit()
    db.session.add(cls(**values))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_coursework_rejects_duplicate_unknown_term_attempt_and_rolls_back(app, make_user):
    user = make_user()
    user_id = user.id
    values = dict(user_id=user_id, code="CSCI 1001", title="Synthetic course",
                  credits=3, status="done", term=None, source="manual")
    original = models.Coursework(**values)
    db.session.add(original)
    db.session.commit()
    original_id = original.id
    db.session.add(models.Coursework(**values))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    rows = db.session.query(models.Coursework).filter_by(user_id=user_id).all()
    assert [row.id for row in rows] == [original_id]


def test_coursework_attempt_identity_allows_other_owners_and_distinct_terms(app, make_user):
    first, second = make_user(), make_user()
    for owner, term in [(first, None), (second, None),
                        (first, "Fall 2025"), (first, "Spring 2026")]:
        db.session.add(models.Coursework(
            user_id=owner.id, code="CSCI 1001", title="Synthetic course",
            credits=3, status="done", term=term, source="manual",
        ))
    db.session.commit()
    assert db.session.query(models.Coursework).count() == 4


def seed_owned_rows(user):
    transcript = models.Transcript(id=uuid4().hex, user_id=user.id, file_name="synthetic.pdf", status="parsed")
    plan = models.Plan(user_id=user.id)
    db.session.add_all([transcript, plan])
    db.session.flush()
    coursework = models.Coursework(user_id=user.id, code="CSCI 1001", title="Synthetic course",
                                    credits=3, status="done", source="transcript", transcript_id=transcript.id)
    course = models.PlanCourse(plan_id=plan.id, code="CSCI 1002", term="Spring 2027", source="user")
    db.session.add_all([coursework, course])
    db.session.commit()
    return [(models.Transcript, transcript.id), (models.Plan, plan.id),
            (models.Coursework, coursework.id), (models.PlanCourse, course.id)]


def test_deleting_user_cascades_owned_rows_and_preserves_other_user(app, make_user):
    first, second = make_user(), make_user()
    first_rows, second_rows = seed_owned_rows(first), seed_owned_rows(second)
    db.session.execute(delete(models.User).where(models.User.id == first.id))
    db.session.commit()
    db.session.expire_all()
    for cls, identity in first_rows:
        assert db.session.get(cls, identity) is None
    for cls, identity in second_rows:
        assert db.session.get(cls, identity) is not None


def test_deleting_transcript_preserves_coursework_and_clears_link(app, make_user):
    rows = seed_owned_rows(make_user())
    transcript_id = rows[0][1]
    coursework_id = rows[2][1]
    db.session.execute(delete(models.Transcript).where(models.Transcript.id == transcript_id))
    db.session.commit()
    db.session.expire_all()
    row = db.session.get(models.Coursework, coursework_id)
    assert row is not None
    assert row.transcript_id is None
    assert row.source == "transcript"


def test_existing_user_gets_false_coursework_skipped_default(app):
    downgrade(directory="migrations", revision="6dd8d6e5f05f")
    db.session.execute(text("""
        INSERT INTO users (google_sub, email, created_at, updated_at)
        VALUES ('synthetic-old', 'synthetic-old@example.invalid', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """))
    db.session.commit()
    upgrade(directory="migrations")
    assert "coursework_skipped" in {column["name"] for column in inspect(db.engine).get_columns("users")}
    assert db.session.scalar(text("SELECT coursework_skipped FROM users")) == 0
