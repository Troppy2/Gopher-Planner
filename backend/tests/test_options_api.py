"""Profile options for onboarding and Settings (issue #9)."""
from datetime import date

import pytest


@pytest.fixture
def options_today(monkeypatch):
    from app.services import options

    state = {"value": date(2026, 11, 7)}
    monkeypatch.setattr(options, "today", lambda: state["value"])
    return state


def test_options_require_authentication(client):
    assert client.get("/api/v1/options").status_code == 401


def test_options_list_supported_majors_and_mark_unreviewed(client, make_user, login_as, program_files, monkeypatch):
    from app.services import programs

    monkeypatch.setattr(programs, "REVIEWED_PROGRAM_IDS", frozenset({"rich-synthetic"}))
    login_as(make_user())
    body = client.get("/api/v1/options").json
    assert body["majors"] == ["Mini Synthetic B.S.", "Rich Synthetic B.S.", "Synthetic B.S."]
    assert "Rich Synthetic B.S." not in body["unverifiedMajors"]
    assert "Mini Synthetic B.S." in body["unverifiedMajors"]


def test_options_standings_are_fixed(client, make_user, login_as, program_files):
    login_as(make_user())
    assert client.get("/api/v1/options").json["standings"] == ["Freshman", "Sophomore", "Junior", "Senior"]


def test_graduation_targets_start_after_the_current_term(client, make_user, login_as, program_files, options_today):
    login_as(make_user())
    targets = client.get("/api/v1/options").json["graduationTargets"]
    assert targets[:3] == ["Spring 2027", "Fall 2027", "Spring 2028"]
    assert len(targets) == 12
    assert targets[-1] == "Fall 2032"


def test_graduation_targets_move_with_the_date(client, make_user, login_as, program_files, options_today):
    options_today["value"] = date(2027, 3, 1)
    login_as(make_user())
    assert client.get("/api/v1/options").json["graduationTargets"][0] == "Fall 2027"


def test_subjects_come_from_the_catalog(client, make_user, login_as, program_files, catalog):
    login_as(make_user())
    assert client.get("/api/v1/options").json["subjects"] == ["CSCI", "MATH"]


def test_subjects_are_empty_without_a_catalog(client, make_user, login_as, program_files):
    login_as(make_user())
    assert client.get("/api/v1/options").json["subjects"] == []


def test_careers_only_for_listed_majors_with_suggestions(client, make_user, login_as, program_files, monkeypatch):
    from app.services import options

    monkeypatch.setattr(options, "CAREERS", {"Mini Synthetic B.S.": ["Synthetic career"],
                                             "Not A Supported Major": ["Ignored"]})
    login_as(make_user())
    assert client.get("/api/v1/options").json["careers"] == {"Mini Synthetic B.S.": ["Synthetic career"]}
