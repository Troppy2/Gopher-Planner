"""Public course-version export used to resolve program course IDs. External HTTP is faked."""
import csv

import pytest


def record(**overrides):
    value = {
        "id": "0000011-2026-09-08", "courseGroupId": "0000011", "code": "TEST1001H", "subjectCode": "TEST",
        "courseNumber": "1001H", "name": "Short", "longName": "Synthetic Honors Course",
        "effectiveStartDate": "2026-09-08", "effectiveEndDate": None, "courseTypicallyOffered": "Every Fall",
        "credits": {"repeatable": False, "creditHours": {"min": 3, "max": 4}},
        "description": "Synthetic description.\n\nprereq: TEST 1000 or TEST 0900",
        "customFields": {"cdCourseCurrContactEmail": "private@example.invalid"},
    }
    value.update(overrides)
    return value


def test_course_row_keeps_version_identity_official_title_credits_offering_and_prerequisite_text():
    from scripts.export_courses import course_row

    row = course_row(record(), retrieved_at="2026-11-22T00:00:00Z")
    assert row == {
        "course_group_id": "0000011", "revision_id": "0000011-2026-09-08", "code": "TEST 1001H",
        "title": "Synthetic Honors Course", "credits_min": "3", "credits_max": "4",
        "typically_offered": "Every Fall", "prerequisite_text": "TEST 1000 or TEST 0900", "repeatable": "false",
        "effective_start_date": "2026-09-08", "effective_end_date": "",
        "source_url": "https://umtc.catalog.prod.coursedog.com/courses/0000011",
        "retrieved_at_utc": "2026-11-22T00:00:00Z", "le_attributes": "", "description": "Synthetic description.",
    }


def test_course_row_distinguishes_absent_prerequisite_text_and_omits_contact_fields():
    from scripts.export_courses import course_row

    row = course_row(record(description="No prerequisite statement."), retrieved_at="now")
    assert row["prerequisite_text"] == ""
    assert "private@example.invalid" not in str(row)


class Session:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def post(self, url, params, json, timeout):
        self.calls.append(params["skip"])
        page = self.pages[len(self.calls) - 1]

        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return page

        return Response()


CONFIG = {"catalog_id": "c", "school": "s", "effective_start": "2026-09-08", "effective_end": "2027-12-31"}


def test_course_fetch_collects_every_page_and_rejects_duplicates_or_changing_totals():
    from scripts.export_courses import fetch_courses

    first, second = record(), record(id="0000012-2026-09-08", courseGroupId="0000012")
    session = Session([{"listLength": 2, "data": [first]}, {"listLength": 2, "data": [second]}])
    assert [item["id"] for item in fetch_courses(session, CONFIG)] == [first["id"], second["id"]]
    assert session.calls == [0, 1]
    with pytest.raises(ValueError):
        fetch_courses(Session([{"listLength": 2, "data": [first]}, {"listLength": 2, "data": [first]}]), CONFIG)
    with pytest.raises(ValueError):
        fetch_courses(Session([{"listLength": 2, "data": [first]}, {"listLength": 3, "data": [second]}]), CONFIG)


def test_course_snapshot_refuses_empty_input_and_existing_files(tmp_path):
    from scripts.export_courses import write_courses

    path = tmp_path / "courses.csv"
    with pytest.raises(ValueError):
        write_courses(path, [], retrieved_at="now")
    assert not path.exists()
    write_courses(path, [record()], retrieved_at="now")
    with path.open(encoding="utf-8-sig", newline="") as source:
        assert next(csv.DictReader(source))["code"] == "TEST 1001H"
    with pytest.raises(FileExistsError):
        write_courses(path, [record()], retrieved_at="now")


def test_course_row_keeps_liberal_education_attributes_and_the_description_without_the_prereq_line():
    from scripts.export_courses import course_row

    row = course_row(record(customFields={"catalogAttributes": ["Social Sciences", "Writing Intensive"],
                                          "cdCourseCurrContactEmail": "private@example.invalid"}), retrieved_at="now")
    assert row["le_attributes"] == "Social Sciences; Writing Intensive"
    assert row["description"] == "Synthetic description."
    assert "private@example.invalid" not in str(row)
