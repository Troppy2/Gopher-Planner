"""Version-aware course metadata resolution. Pure functions plus the read-only catalog boundary."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "programs"


def rich():
    return json.loads((FIXTURES / "rich-synthetic--fall-2026.json").read_text(encoding="utf-8"))


def catalog_row(code="TEST 1001", *, version="unknown", title="Synthetic intro A", minimum=3, maximum=3,
                offered="Every Fall & Spring", prerequisites=None, status="none", unresolved=()):
    return {"code": code, "title": title, "minimumCredits": minimum, "maximumCredits": maximum,
            "typicallyOffered": offered, "catalogVersion": version,
            "prerequisiteJson": {"status": status, "requirements": prerequisites},
            "unresolvedPrerequisites": list(unresolved)}


def resolve(code, program, row):
    from app.services.metadata import resolve_course
    return resolve_course(code, program, row)


def test_supplemental_only_course_resolves_title_and_credits_from_the_program():
    result = resolve("TEST 1003", rich(), None)
    assert (result["title"], result["minimumCredits"], result["maximumCredits"]) == ("Synthetic intro substitute", 4, 4)
    assert result["metadataSource"] == "program"
    assert result["blockedReason"] is None
    assert result["prerequisites"] == {"state": "verified_none", "expression": None}


def test_course_known_to_neither_source_is_unknown_instead_of_guessed():
    assert resolve("ZZZZ 9999", rich(), None) is None
    assert resolve("ZZZZ 9999", None, None) is None


def test_compatible_catalog_record_takes_precedence_when_sources_agree():
    row = catalog_row(version="synthetic-2026", offered="Every Fall & Spring")
    result = resolve("TEST 1001", rich(), row)
    assert result["metadataSource"] == "catalog"
    assert result["metadataWarnings"] == []
    assert result["offered"] == ["Fall", "Spring"]


def test_target_version_supplement_overrides_unknown_version_legacy_catalog_facts():
    row = catalog_row(title="Legacy title", minimum=4, maximum=4, offered="Every Fall")
    result = resolve("TEST 1001", rich(), row)
    assert (result["metadataSource"], result["title"], result["minimumCredits"]) == ("program", "Synthetic intro A", 3)
    assert result["offered"] == ["Fall", "Spring"]
    assert "catalog_metadata_conflict" not in result["metadataWarnings"]


def test_conflicting_verified_compatible_sources_block_placement():
    row = catalog_row(version="synthetic-2026", minimum=4, maximum=4)
    result = resolve("TEST 1001", rich(), row)
    assert "catalog_metadata_conflict" in result["metadataWarnings"]
    assert result["blockedReason"] == "catalog_metadata_conflict"


def test_legacy_catalog_only_course_is_visible_but_flagged_unverified():
    row = catalog_row("CSCI 1001", title="Synthetic catalog course", minimum=4, maximum=4, offered="Every Fall")
    result = resolve("CSCI 1001", rich(), row)
    assert (result["metadataSource"], result["title"], result["offered"]) == ("catalog", "Synthetic catalog course", ["Fall"])
    assert "catalog_version_unverified" in result["metadataWarnings"]
    assert result["blockedReason"] is None


@pytest.mark.parametrize("offered", ["-", "", None])
def test_missing_legacy_offering_data_is_unknown_rather_than_every_term(offered):
    result = resolve("CSCI 1001", None, catalog_row("CSCI 1001", offered=offered))
    assert result["offered"] is None
    assert "offered_terms_unverified" in result["metadataWarnings"]


def test_periodic_offerings_keep_their_season_with_a_verification_warning():
    result = resolve("CSCI 1001", None, catalog_row("CSCI 1001", offered="Periodic Spring"))
    assert result["offered"] == ["Spring"]
    assert "offered_terms_unverified" in result["metadataWarnings"]


def test_unknown_supplemental_offering_is_flagged_but_not_blocked():
    result = resolve("MATH 3001", rich(), None)
    assert result["offered"] is None
    assert "offered_terms_unverified" in result["metadataWarnings"]
    assert result["blockedReason"] is None


def test_unknown_prerequisites_block_placement_unlike_verified_empty_prerequisites():
    unknown = resolve("TEST 3003", rich(), None)
    assert unknown["prerequisites"]["state"] == "unknown"
    assert unknown["blockedReason"] == "course_metadata_unavailable"
    assert "course_metadata_unavailable" in unknown["metadataWarnings"]
    verified = resolve("TEST 1001", rich(), None)
    assert verified["prerequisites"]["state"] == "verified_none"


def test_missing_catalog_prerequisite_record_is_unknown():
    row = catalog_row("CSCI 1001")
    row["prerequisiteJson"] = None
    result = resolve("CSCI 1001", None, row)
    assert result["prerequisites"]["state"] == "unknown"
    assert result["blockedReason"] == "course_metadata_unavailable"


def test_catalog_prerequisite_codes_are_normalized_and_conditions_require_review():
    tree = {"type": "all_of", "requirements": [{"type": "course", "course_code": "CSci 1913"},
                                               {"type": "condition", "text": "Synthetic standing"}]}
    result = resolve("CSCI 1001", None, catalog_row("CSCI 1001", prerequisites=tree, status="found"))
    assert result["prerequisites"]["state"] == "tree"
    assert result["prerequisites"]["expression"]["requirements"][0]["course_code"] == "CSCI 1913"
    assert "prerequisites_require_review" in result["metadataWarnings"]
    assert result["blockedReason"] is None


def test_unresolved_catalog_prerequisite_references_require_review():
    tree = {"type": "course", "course_code": "CSCI 1001"}
    result = resolve("CSCI 1002", None, catalog_row("CSCI 1002", prerequisites=tree, status="found", unresolved=["EE 1301"]))
    assert "prerequisites_require_review" in result["metadataWarnings"]


def test_resolution_does_not_mutate_program_or_catalog_inputs():
    program, row = rich(), catalog_row(version="synthetic-2026")
    snapshot = copy.deepcopy((program, row))
    resolve("TEST 1001", program, row)
    assert (program, row) == snapshot


def test_metadata_coverage_reports_referenced_courses_without_authoritative_title_or_credits():
    from app.services.metadata import coverage_gaps

    program = rich()
    del program["courseMetadata"]["TEST 3003"]
    assert coverage_gaps(program, catalog_codes={"TEST 1001"}) == ["TEST 3003"]
    assert coverage_gaps(program, catalog_codes={"TEST 3003"}) == []


def test_catalog_repository_reads_versioned_records_without_writing_the_catalog(catalog):
    from app.repositories.catalog import find_courses

    before = hashlib.sha256(catalog.read_bytes()).hexdigest()
    rows = find_courses(["CSCI 1002", "MATH 2007", "ZZZZ 9999"])
    assert set(rows) == {"CSCI 1002", "MATH 2007"}
    assert rows["CSCI 1002"]["catalogVersion"] == "synthetic"
    assert rows["CSCI 1002"]["prerequisiteJson"]["requirements"] == {"type": "course", "course_code": "CSCI 1001"}
    assert rows["CSCI 1002"]["minimumCredits"] == 3
    assert hashlib.sha256(catalog.read_bytes()).hexdigest() == before


def test_shipped_catalog_imports_read_only(app):
    from pathlib import Path

    from app.repositories.catalog import find_courses
    from app.services.catalog_import import import_catalog

    shipped = Path(__file__).resolve().parents[1] / "data" / "courses.db"
    before = hashlib.sha256(shipped.read_bytes()).hexdigest()
    assert import_catalog(shipped)["courses"] == 324
    assert "CSCI 1133" in find_courses(["CSCI 1133"])
    assert hashlib.sha256(shipped.read_bytes()).hexdigest() == before


def test_program_equivalents_keep_a_concurrent_prerequisite_concurrent():
    from app.services.metadata import with_equivalents

    expanded = with_equivalents({"type": "course", "course_code": "MATH 1372", "concurrent": True},
                                {"MATH 1372": {"MATH 1372", "MATH 1272"}})
    assert expanded == {"type": "any_of", "requirements": [
        {"type": "course", "course_code": "MATH 1372", "concurrent": True},
        {"type": "course", "course_code": "MATH 1272", "concurrent": True}]}
