"""Supported program listing for major selection."""


def test_program_listing_requires_authentication(client):
    assert client.get("/api/v1/programs").status_code == 401


def test_program_listing_returns_supported_names_and_catalog_terms(client, make_user, login_as, program_files):
    login_as(make_user())
    response = client.get("/api/v1/programs")
    assert response.status_code == 200
    programs = {item["name"]: item for item in response.json["programs"]}
    assert programs["Mini Synthetic B.S."]["catalogTerms"] == ["Fall 2026"]
    assert programs["Rich Synthetic B.S."]["officialName"] == "Rich Synthetic Bachelor of Science"
    assert programs["Mini Synthetic B.S."]["officialName"] == "Mini Synthetic B.S."
    assert [item["name"] for item in response.json["programs"]] == sorted(programs)


def test_program_listing_marks_only_hand_reviewed_programs(client, make_user, login_as, program_files, monkeypatch):
    from app.services import programs

    monkeypatch.setattr(programs, "REVIEWED_PROGRAM_IDS", frozenset({"rich-synthetic"}))
    login_as(make_user())
    listed = {item["name"]: item["reviewed"] for item in client.get("/api/v1/programs").json["programs"]}
    assert listed["Rich Synthetic B.S."] is True
    assert listed["Mini Synthetic B.S."] is False
