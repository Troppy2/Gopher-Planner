"""DELETE /api/v1/auth/account removes the signed-in user and only their data."""
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app import models
from app.extensions import db


def seed_owned_rows(user):
    transcript = models.Transcript(id=uuid4().hex, user_id=user.id, file_name="synthetic.pdf", status="parsed")
    plan = models.Plan(user_id=user.id)
    db.session.add_all([transcript, plan])
    db.session.flush()
    db.session.add_all([
        models.Coursework(user_id=user.id, code="CSCI 1001", title="Synthetic course", credits=Decimal("4"),
                          status="done", term=None, grade=None, source="transcript", transcript_id=transcript.id),
        models.PlanCourse(plan_id=plan.id, code="CSCI 2001", term="Spring 2027", source="user"),
    ])
    db.session.commit()


def owned_counts(user_id):
    plan_ids = select(models.Plan.id).where(models.Plan.user_id == user_id)
    return {
        "users": db.session.scalar(select(func.count()).select_from(models.User).where(models.User.id == user_id)),
        "sessions": db.session.scalar(select(func.count()).select_from(models.UserSession).where(models.UserSession.user_id == user_id)),
        "transcripts": db.session.scalar(select(func.count()).select_from(models.Transcript).where(models.Transcript.user_id == user_id)),
        "coursework": db.session.scalar(select(func.count()).select_from(models.Coursework).where(models.Coursework.user_id == user_id)),
        "plans": db.session.scalar(select(func.count()).select_from(models.Plan).where(models.Plan.user_id == user_id)),
        "plan_courses": db.session.scalar(select(func.count()).select_from(models.PlanCourse).where(models.PlanCourse.plan_id.in_(plan_ids))),
    }


def test_delete_account_removes_user_data_and_keeps_others(client, make_user, login_as, post_headers):
    other = make_user()
    seed_owned_rows(other)
    login_as(other)
    user = make_user()
    seed_owned_rows(user)
    login_as(user)
    user_id, other_id = user.id, other.id

    response = client.delete("/api/v1/auth/account", json={"confirm": True}, headers=post_headers)

    assert response.status_code == 200
    assert "gp_session=;" in response.headers["Set-Cookie"]
    db.session.expire_all()
    assert set(owned_counts(user_id).values()) == {0}
    assert set(owned_counts(other_id).values()) == {1}
    assert client.get("/api/v1/profile").status_code == 401


@pytest.mark.parametrize("body", [None, {}, {"confirm": "true"}, {"confirm": False}])
def test_delete_account_requires_explicit_confirmation(client, make_user, login_as, post_headers, body):
    user = make_user()
    login_as(user)
    response = client.delete("/api/v1/auth/account", json=body, headers=post_headers)
    assert response.status_code == 400
    assert client.get("/api/v1/profile").status_code == 200


def test_delete_account_requires_sign_in(client, post_headers):
    response = client.delete("/api/v1/auth/account", json={"confirm": True}, headers=post_headers)
    assert response.status_code == 401


def test_delete_account_rejects_wrong_origin(client, make_user, login_as):
    login_as(make_user())
    response = client.delete("/api/v1/auth/account", json={"confirm": True},
                             headers={"Origin": "http://untrusted.invalid"})
    assert response.status_code == 403
    assert client.get("/api/v1/profile").status_code == 200
