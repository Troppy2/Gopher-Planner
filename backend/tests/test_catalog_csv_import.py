"""Full-catalog CSV export merged with the reviewed SQLite export. Rows are synthetic."""
import csv
import json

from sqlalchemy import select

from tests.test_catalog_store import counts

FIELDS = ["course_group_id", "revision_id", "code", "title", "credits_min", "credits_max", "typically_offered",
          "prerequisite_text", "repeatable", "effective_start_date", "effective_end_date", "source_url",
          "retrieved_at_utc", "le_attributes", "description"]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    return path


def row(code, **values):
    base = {"course_group_id": "g-" + code, "revision_id": f"g-{code}-2020-01-01", "code": code,
            "title": f"Synthetic {code}", "credits_min": "3", "credits_max": "3",
            "typically_offered": "Every Fall", "repeatable": "false", "effective_start_date": "2020-01-01"}
    base.update(values)
    return base


def by_code(code):
    from app.extensions import db
    from app.models import CatalogCourse

    return db.session.scalars(select(CatalogCourse).where(CatalogCourse.course_code == code)).one_or_none()


def test_csv_adds_other_subjects_and_reviewed_rows_win(app, catalog, tmp_path):
    from app.services.catalog_import import import_catalog

    extra = write_csv(tmp_path / "all.csv", [
        row("CSCI 1001", title="Should not replace reviewed row"),
        row("CHEM 1061", prerequisite_text="Prereq: MATH 1031 or instructor consent", credits_min="4",
            credits_max="4", repeatable="true"),
        row("HIST 1001"),
    ])
    result = import_catalog(catalog, extra_csv=extra)
    assert counts() == (1, 14, 1)
    assert result["courses"] == 14
    assert by_code("CSCI 1001").course_name == "Synthetic course 1"
    chem = by_code("CHEM 1061")
    assert (chem.subject_code, chem.course_number, chem.minimum_credits, chem.repeatable) == ("CHEM", "1061", "4", "Yes")
    assert chem.prerequisite_status == "text_only"
    assert json.loads(chem.prerequisite_json) == {
        "status": "found", "needs_review": True, "source_text": "Prereq: MATH 1031 or instructor consent",
        "requirements": {"type": "condition", "text": "Prereq: MATH 1031 or instructor consent"}}
    assert json.loads(by_code("HIST 1001").prerequisite_json)["status"] == "none"
    assert by_code("HIST 1001").prerequisite_status == "none"


def test_csv_skips_retired_and_future_revisions_and_keeps_latest_duplicate(app, catalog, tmp_path):
    from app.services.catalog_import import import_catalog

    extra = write_csv(tmp_path / "all.csv", [
        row("OLD 1000", effective_end_date="2021-01-01"),
        row("NEW 1000", effective_start_date="2999-01-01"),
        row("DUP 4960", credits_min="4", credits_max="4"),
        row("DUP 4960", effective_start_date="2026-05-18", credits_min="3", credits_max="3"),
    ])
    import_catalog(catalog, extra_csv=extra, today="2026-11-23")
    assert by_code("OLD 1000") is None and by_code("NEW 1000") is None
    assert by_code("DUP 4960").minimum_credits == "3"


def test_text_only_prerequisites_warn_but_never_block(app, catalog, tmp_path):
    from app.services.catalog_import import import_catalog
    from app.repositories.catalog import find_courses
    from app.services.metadata import resolve_course

    import_catalog(catalog, extra_csv=write_csv(tmp_path / "all.csv", [
        row("CHEM 1061", prerequisite_text="MATH 1031 or instructor consent"), row("HIST 1001")]))
    rows = find_courses(["CHEM 1061", "HIST 1001"])
    chem = resolve_course("CHEM 1061", None, rows["CHEM 1061"])
    assert chem["blockedReason"] is None
    assert "prerequisites_require_review" in chem["metadataWarnings"]
    assert resolve_course("HIST 1001", None, rows["HIST 1001"])["prerequisites"]["state"] == "verified_none"


def test_import_without_csv_is_unchanged(app, catalog):
    from app.services.catalog_import import import_catalog

    import_catalog(catalog)
    assert counts() == (1, 12, 1)


def test_csv_le_attributes_and_descriptions_reach_every_course_including_reviewed_rows(app, catalog, tmp_path):
    from app.services.catalog_import import import_catalog

    import_catalog(catalog, extra_csv=write_csv(tmp_path / "all.csv", [
        row("CSCI 1001", le_attributes="Writing Intensive", description="Reviewed row description"),
        row("HIST 1001", le_attributes="Global Perspectives; Historical Perspectives", description="Synthetic history"),
        row("CHEM 1061"),
    ]))
    assert by_code("HIST 1001").le_attributes == "Global Perspectives; Historical Perspectives"
    assert by_code("HIST 1001").description == "Synthetic history"
    assert by_code("CSCI 1001").le_attributes == "Writing Intensive"
    assert by_code("CSCI 1001").course_name == "Synthetic course 1"
    assert by_code("CHEM 1061").le_attributes == ""
    assert by_code("CSCI 1002").le_attributes == ""


def test_le_queries_report_coverage_and_suggest_prerequisite_free_courses_in_season(app, catalog, tmp_path):
    from app.repositories.catalog import le_coverage, suggest_le_course
    from app.services.catalog_import import import_catalog

    import_catalog(catalog, extra_csv=write_csv(tmp_path / "all.csv", [
        row("HIST 1001", le_attributes="Global Perspectives; Historical Perspectives", typically_offered="Every Fall"),
        row("GLOB 3001", le_attributes="Global Perspectives", typically_offered="Every Fall & Spring"),
        row("GLOB 1002", le_attributes="Global Perspectives", typically_offered="Every Spring"),
        row("GLOB 1003", le_attributes="Global Perspectives", prerequisite_text="HIST 1001"),
        row("ARTS 1001", le_attributes="Arts/Humanities; Writing Intensive"),
    ]))
    assert le_coverage(["ARTS 1001", "NOPE 1000"]) == {"Arts/Humanities", "Writing Intensive"}
    code, covered = suggest_le_course(["Global Perspectives", "Historical Perspectives"], season="Fall", exclude=set())
    assert (code, covered) == ("HIST 1001", ["Global Perspectives", "Historical Perspectives"])
    assert suggest_le_course(["Global Perspectives"], season="Spring", exclude=set())[0] == "GLOB 1002"
    assert suggest_le_course(["Global Perspectives"], season="Fall", exclude={"HIST 1001"})[0] == "GLOB 3001"
    assert suggest_le_course(["Literature"], season="Fall", exclude=set()) is None


def test_le_suggestions_skip_restricted_courses_and_prefer_yearly_offerings(app, catalog, tmp_path):
    from app.repositories.catalog import le_candidates, open_to_any_undergraduate, suggest_le_course
    from app.services.catalog_import import import_catalog

    import_catalog(catalog, extra_csv=write_csv(tmp_path / "all.csv", [
        row("GLOB 1001H", le_attributes="Global Perspectives"),
        row("GLOB 1905", le_attributes="Global Perspectives", title="Freshman Seminar"),
        row("GLOB 5001", le_attributes="Global Perspectives"),
        row("GLOB 1102", le_attributes="Global Perspectives", typically_offered="Periodic Fall"),
        row("GLOB 3003", le_attributes="Global Perspectives", typically_offered="Every Fall"),
    ]))
    assert not open_to_any_undergraduate("GLOB 1001H", "Honors")
    assert not open_to_any_undergraduate("GLOB 1905", "Topics: Freshman Seminar")
    assert not open_to_any_undergraduate("GLOB 5001", "Graduate topics")
    assert open_to_any_undergraduate("GLOB 3003", "Global topics")
    assert suggest_le_course(["Global Perspectives"], season="Fall", exclude=set())[0] == "GLOB 3003"
    pool = [code for code, _ in le_candidates([("Global", {"Global Perspectives"})], exclude=set())]
    assert pool == ["GLOB 1102", "GLOB 3003"]


def test_fully_parsed_prerequisites_become_trees_and_unknown_courses_stay_text(app, catalog, tmp_path):
    from app.services.catalog_import import import_catalog

    import_catalog(catalog, extra_csv=write_csv(tmp_path / "all.csv", [
        row("HIST 1001"), row("HIST 3001", prerequisite_text="1001 or 1002"),
        row("HIST 3002", prerequisite_text="HIST 1001, GONE 1000")]))
    later = by_code("HIST 3001")
    assert later.prerequisite_status == "found"
    assert json.loads(later.prerequisite_json)["requirements"] == {"type": "course", "course_code": "HIST 1001"}
    assert by_code("HIST 3002").prerequisite_status == "text_only"


def test_enforced_requirements_and_reviewed_trees_take_precedence(app, catalog, tmp_path):
    from app.services.catalog_import import import_catalog

    requisites = tmp_path / "requisites.csv"
    with requisites.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, ["term", "strm", "code", "course_id", "requirement_group", "requirement_text",
                                         "sections", "source_url", "retrieved_at_utc"])
        writer.writeheader()
        for code, text in [("NSCI 3101", "NSci 2001 or 2101"), ("NSCI 3102", "Neuroscience majors only")]:
            writer.writerow({"term": "Spring 2027", "strm": "1273", "code": code, "course_id": "1", "requirement_group": "1",
                             "requirement_text": text, "sections": 1, "source_url": "https://example.test",
                             "retrieved_at_utc": "2026-11-24T00:00:00+00:00"})
    reviewed = tmp_path / "reviewed.json"
    reviewed.write_text(json.dumps({"sources": {"synthetic": {"url": "https://example.test", "retrieved": "2026-11-24",
                                                              "section": "synthetic"}},
                                    "courses": {"CSCI 1001": {"expression": None, "sourceRef": "synthetic"}}}))
    import_catalog(catalog, extra_csv=write_csv(tmp_path / "all.csv", [
        row("NSCI 2001"), row("NSCI 2101"), row("NSCI 3101"), row("NSCI 3102")]),
        requisites=requisites, reviewed=reviewed)
    assert json.loads(by_code("NSCI 3101").prerequisite_json)["requirements"]["type"] == "any_of"
    # An enforced requirement that can't be parsed still keeps the course out of "no prerequisites".
    assert by_code("NSCI 3102").prerequisite_status == "text_only"
    assert by_code("CSCI 1001").prerequisite_status == "none"
