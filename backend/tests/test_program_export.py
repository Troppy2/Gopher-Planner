import importlib.util
import csv
import json

import pytest


def test_program_export_preserves_versioned_identity_and_nested_requirement_rules():
    assert importlib.util.find_spec("scripts.export_programs") is not None, "Missing program CSV exporter"
    from scripts.export_programs import program_row

    rules = {"requisitesSimple": [{"id": "synthetic-core", "rules": [
        {"condition": "anyOf", "subRules": [
            {"id": "pair", "condition": "allOf", "subRules": [{"id": "first"}, {"id": "second"}]},
            {"id": "alternative"},
        ]},
    ]}]}
    record = {
        "id": "synthetic-2026-09-08", "programGroupId": "synthetic", "code": "TEST",
        "catalogDisplayName": "Synthetic B.S.", "campus": "Twin Cities", "career": "Undergraduate",
        "type": "Major", "effectiveStartDate": "2026-09-08", "effectiveEndDate": None,
        "requisites": rules, "requirementLevels": [{"key": "core", "notes": "Synthetic waiver"}],
        "customFields": {"cdProgramCreditsDegreeMin": "120", "cdProgramCreditsProgramMin": "78"},
    }
    row = program_row(record, catalog_id="synthetic-catalog", retrieved_at="2026-11-22T12:00:00Z")
    assert row["program_id"] == "synthetic"
    assert row["revision_id"] == "synthetic-2026-09-08"
    assert row["effective_start_date"] == "2026-09-08"
    assert row["effective_end_date"] == ""
    assert row["degree_credits_min"] == "120"
    assert row["program_credits_min"] == "78"
    assert json.loads(row["requirements_json"]) == rules
    assert json.loads(row["requirement_levels_json"]) == record["requirementLevels"]
    assert row["source_url"] == "https://umtc.catalog.prod.coursedog.com/programs/synthetic"


def test_export_discovers_catalog_and_filters_from_the_published_page_instead_of_cached_dates():
    from scripts import export_programs

    assert hasattr(export_programs, "discover_catalog"), "Missing current catalog discovery"
    nodes = [
        {"pinia": 1}, ["Reactive", 2], {"settings": 3},
        {"activeCatalog": 4, "school": 5, "effectiveDatesRange": 6, "programsFilters": 9},
        "synthetic-next-catalog", "synthetic-school",
        {"effectiveStartDate": 7, "effectiveEndDate": 8}, "2028-01-01", "2029-01-01",
        {"condition": 10, "filters": 11}, "and", [],
    ]
    html = '<html><script id="__NUXT_DATA__" type="application/json">' + json.dumps(nodes) + '</script></html>'
    result = export_programs.discover_catalog(html)
    assert result == {
        "catalog_id": "synthetic-next-catalog", "school": "synthetic-school",
        "effective_start": "2028-01-01", "effective_end": "2029-01-01",
        "filters": {"condition": "and", "filters": []},
    }


def test_export_fetches_every_page_when_server_caps_the_requested_page_size():
    from scripts import export_programs

    assert hasattr(export_programs, "fetch_programs"), "Missing complete program pagination"
    calls = []

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    class PublicCatalog:
        def post(self, url, *, params, json, timeout):
            calls.append((url, params.copy(), json, timeout))
            start = params["skip"]
            return Response({"listLength": 3, "data": [
                {"id": f"synthetic-{i}", "programGroupId": f"program-{i}"}
                for i in range(start, min(start + 2, 3))
            ]})

    config = {"school": "synthetic", "catalog_id": "catalog", "effective_start": "2026-01-01",
              "effective_end": "2027-01-01", "filters": {"condition": "and", "filters": []}}
    records = export_programs.fetch_programs(PublicCatalog(), config)
    assert [record["id"] for record in records] == ["synthetic-0", "synthetic-1", "synthetic-2"]
    assert [call[1]["skip"] for call in calls] == [0, 2]
    assert all(call[1]["effectiveDatesRange"] == "2026-01-01,2027-01-01" for call in calls)
    assert all(call[2] == {"condition": "AND", "filters": [config["filters"]]} for call in calls)


@pytest.mark.parametrize("page", [
    {"listLength": 2, "data": []},
    {"listLength": 2, "data": [{"id": "same"}, {"id": "same"}]},
])
def test_export_refuses_incomplete_or_duplicate_records_instead_of_claiming_complete_coverage(page):
    from scripts.export_programs import fetch_programs

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return page

    class PublicCatalog:
        def post(self, *args, **kwargs):
            return Response()

    config = {"school": "synthetic", "catalog_id": "catalog", "effective_start": "2026-01-01",
              "effective_end": "2027-01-01", "filters": {}}
    with pytest.raises(ValueError, match="incomplete|duplicate"):
        fetch_programs(PublicCatalog(), config)


def test_export_writes_a_lossless_csv_snapshot_with_dates_metadata_and_content_hash(tmp_path):
    from scripts import export_programs

    assert hasattr(export_programs, "write_snapshot"), "Missing reusable CSV snapshot writer"
    rules = {"requisitesSimple": [{"name": 'Synthetic "quoted" group', "notes": "Line one\nLine two",
                                  "rules": [{"condition": "anyOf", "subRules": [{"id": "a"}, {"id": "b"}]}]}]}
    record = {"id": "synthetic-revision", "programGroupId": "synthetic", "name": "Synthetic, B.S.",
              "requisites": rules, "requirementLevels": [], "effectiveStartDate": "2026-09-08",
              "customFields": {"cdProgramCreditsDegreeMax": "124", "cdProgramCreditsProgramMax": "80",
                               "cdProgramReqLanguageUgrd": "Synthetic language rule", "newAcademicRule": "Keep unknown source facts",
                               "cdProgramCurrContactEmail": "staff@example.invalid"}}
    config = {"catalog_id": "synthetic-catalog", "school": "synthetic",
              "effective_start": "2026-09-08", "effective_end": "2027-09-07", "filters": {}}
    path = tmp_path / "programs.csv"
    export_programs.write_snapshot(path, [record], config, retrieved_at="2026-11-22T12:00:00Z")
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Synthetic, B.S."
    assert json.loads(row["requirements_json"]) == rules
    assert row["degree_credits_max"] == "124"
    assert row["program_credits_max"] == "80"
    assert row["source_window_start"] == "2026-09-08"
    assert row["source_window_end"] == "2027-09-07"
    custom = json.loads(row["academic_metadata_json"])
    assert custom["cdProgramReqLanguageUgrd"] == "Synthetic language rule"
    assert custom["newAcademicRule"] == "Keep unknown source facts"
    assert "cdProgramCurrContactEmail" not in custom
    assert len(row["academic_content_sha256"]) == 64
    second = tmp_path / "second.csv"
    export_programs.write_snapshot(second, [record], config, retrieved_at="2027-01-01T12:00:00Z")
    with second.open(encoding="utf-8-sig", newline="") as source:
        assert next(csv.DictReader(source))["academic_content_sha256"] == row["academic_content_sha256"]


def test_refresh_command_reads_public_catalog_and_writes_a_new_snapshot(tmp_path, monkeypatch):
    from scripts import export_programs
    import requests
    from types import SimpleNamespace

    assert hasattr(export_programs, "main"), "Missing semester refresh command"
    nodes = [{"pinia": 1}, ["Reactive", 2], {"settings": 3},
             {"activeCatalog": 4, "school": 5, "effectiveDatesRange": 6, "programsFilters": 9},
             "synthetic-catalog", "synthetic-school", {"effectiveStartDate": 7, "effectiveEndDate": 8},
             "2026-09-08", "2027-09-07", {"condition": 10, "filters": 11}, "and", []]
    html = '<script id="__NUXT_DATA__">' + json.dumps(nodes) + '</script>'
    record = {"id": "synthetic-revision", "programGroupId": "synthetic", "name": "Synthetic major",
              "requisites": {"requisitesSimple": []}}
    headers = {}

    class PublicCatalog:
        def __enter__(self):
            self.headers = headers
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, *, timeout):
            assert url == "https://umtc.catalog.prod.coursedog.com/programs"
            return SimpleNamespace(text=html, raise_for_status=lambda: None)

        def post(self, url, *, params, json, timeout):
            return SimpleNamespace(raise_for_status=lambda: None,
                                   json=lambda: {"listLength": 1, "data": [record]})

    monkeypatch.setattr(requests, "Session", PublicCatalog)
    output = tmp_path / "new-snapshot.csv"
    assert export_programs.main(["--output", str(output)]) == 0
    with output.open(encoding="utf-8-sig", newline="") as source:
        assert next(csv.DictReader(source))["revision_id"] == "synthetic-revision"
    assert headers["x-requested-with"] == "catalog"
    assert headers["Origin"] == "https://umtc.catalog.prod.coursedog.com"


def test_export_preserves_source_punctuation_in_json_without_adding_literal_em_dashes():
    from scripts.export_programs import program_row

    description = "Synthetic source " + chr(0x2014) + " exact punctuation"
    row = program_row({"id": "revision", "programGroupId": "synthetic", "description": description},
                      catalog_id="catalog", retrieved_at="2026-11-22T12:00:00Z")
    assert "description_json" in row
    assert json.loads(row["description_json"]) == description
    assert chr(0x2014) not in row["description_json"]


def test_export_paginates_by_unique_revision_id_to_avoid_unstable_equal_program_names():
    from scripts.export_programs import fetch_programs
    from types import SimpleNamespace

    params_seen = []

    class PublicCatalog:
        def post(self, url, *, params, json, timeout):
            params_seen.append(params)
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"listLength": 0, "data": []})

    config = {"school": "synthetic", "catalog_id": "catalog", "effective_start": "2026-01-01",
              "effective_end": "2027-01-01", "filters": {}}
    assert fetch_programs(PublicCatalog(), config) == []
    assert params_seen[0]["sortBy"] == "id"


def test_export_rejects_catalog_count_changes_between_pages():
    from scripts.export_programs import fetch_programs
    from types import SimpleNamespace

    pages = iter([
        {"listLength": 3, "data": [{"id": "a"}, {"id": "b"}]},
        {"listLength": 2, "data": []},
    ])

    class PublicCatalog:
        def post(self, *args, **kwargs):
            page = next(pages)
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: page)

    config = {"school": "synthetic", "catalog_id": "catalog", "effective_start": "2026-01-01",
              "effective_end": "2027-01-01", "filters": {}}
    with pytest.raises(ValueError, match="changed"):
        fetch_programs(PublicCatalog(), config)


def test_export_rejects_an_empty_snapshot_without_creating_an_output_file(tmp_path):
    from scripts.export_programs import write_snapshot

    path = tmp_path / "must-not-exist.csv"
    config = {"catalog_id": "synthetic", "effective_start": "2026-01-01", "effective_end": "2027-01-01"}
    try:
        write_snapshot(path, [], config, retrieved_at="2026-11-22T12:00:00Z")
    except Exception as error:
        assert not path.exists(), "An empty snapshot must not leave a zero-byte file"
        assert isinstance(error, ValueError)
        assert "empty" in str(error)
    else:
        pytest.fail("An empty snapshot must be rejected")
