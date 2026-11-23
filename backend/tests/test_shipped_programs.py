"""Source-integrity checks for shipped program files. These do not validate academic truth by self-comparison:
each file is traced back to the official snapshot it was mapped from."""
import csv
import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"
PROGRAMS = DATA / "programs"
SNAPSHOT = DATA / "catalog-exports" / "programs.2026-11-22.csv"


@pytest.fixture(scope="module")
def snapshot():
    csv.field_size_limit(100_000_000)
    with SNAPSHOT.open(encoding="utf-8-sig", newline="") as source:
        return {row["program_id"]: row for row in csv.DictReader(source)}


@pytest.fixture(scope="module")
def shipped():
    from app.services.programs import _index, clear_program_cache

    clear_program_cache()
    return list(_index(PROGRAMS).values())


def test_every_undergraduate_major_in_the_snapshot_has_one_valid_versioned_file(shipped, snapshot):
    majors = {pid for pid, row in snapshot.items() if row["career"] == "Undergraduate" and row["program_type"] == "Major"}
    assert {program["officialProgramId"] for program in shipped} == majors
    assert len(shipped) == len(majors)
    graduate = {pid for pid, row in snapshot.items() if row["career"] != "Undergraduate"}
    assert not graduate & {program["officialProgramId"] for program in shipped}


def test_shipped_versions_and_totals_match_their_official_revision(shipped, snapshot):
    for program in shipped:
        row = snapshot[program["officialProgramId"]]
        assert program["totalCredits"] == float(row["degree_credits_min"])
        assert program["sources"]["program"]["url"] == row["source_url"]
        assert row["revision_id"] in program["sources"]["program"]["section"]
        year, month = int(row["effective_start_date"][:4]), int(row["effective_start_date"][5:7])
        assert program["catalogTerm"] == f"{'Spring' if month <= 5 else 'Fall'} {year}"


def test_every_referenced_course_has_sourced_title_and_credits(shipped):
    from app.services.metadata import coverage_gaps

    for program in shipped:
        assert coverage_gaps(program, catalog_codes=set()) == [], program["name"]
        for record in program["courseMetadata"].values():
            assert program["sources"][record["sourceRef"]]["url"].startswith("https://umtc.catalog.prod.coursedog.com/courses/")


def native_rule_ids(row):
    found = set()

    def walk(value):
        if isinstance(value, dict):
            if "id" in value:
                found.add(value["id"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(json.loads(row["requirements_json"]))
    return found


def test_computer_science_fall_2026_traces_every_rule_to_the_official_revision_or_reviewed_overlay(shipped, snapshot):
    program = next(item for item in shipped if item["name"] == "Computer Science B.S.")
    row = snapshot["019627107"]
    assert (program["catalogTerm"], program["totalCredits"], row["revision_id"]) == ("Fall 2026", 120, "019627107-2026-09-08")
    assert program["officialName"] == "Computer Science B.S. Comp.Sc."
    native = native_rule_ids(row)
    overlay = json.loads((Path(__file__).resolve().parents[1] / "scripts" / "program_overlays" / "019627107.json").read_text(encoding="utf-8"))
    overlay_ids = set()

    def collect(node):
        overlay_ids.add(node["id"])
        for child in node.get("children", []):
            collect(child)

    for rule in overlay["replaceRules"].values():
        collect(rule)

    def check(node):
        identity = node["id"]
        base = identity.split("-", 1)[1].split("-")[0] if identity.startswith(("r-", "g-")) else None
        assert identity in overlay_ids or base in native or identity.startswith(("g-notes-", "r-notes-")), identity
        for child in node.get("children", []):
            check(child)

    for group in program["groups"]:
        check(group)
        check(group["rule"])
        assert group.get("gradePolicy", {}).get("sourceRef") in {None, "cs-guide"}
    labels = {group["label"] for group in program["groups"]}
    assert {"Mathematics Core", "Computer Science Introductory Core", "Science Requirements", "Computer Science Core",
            "Technical Electives & Upper Division Math-Oriented Requirement",
            "Upper Division Writing Intensive within the major"} <= labels
    assert [adjustment["whenAnySatisfied"] for adjustment in program["adjustments"]] == [["r-8gCeXIfT", "r-ED4mbHRX"]]


def test_computer_science_requires_the_sourced_elective_total_and_csci_subminimum(shipped):
    from app.services.requirements import evaluate_program

    program = next(item for item in shipped if item["name"] == "Computer Science B.S.")
    electives = [{"code": code, "grade": "A", "status": "done", "credits": 4, "term": "Fall 2025"}
                 for code in ("CSCI 5521", "CSCI 5523", "MATH 4242")]
    result = {item["id"]: item for item in evaluate_program(program, electives)["requirementProgress"]}
    total = result["cs-technical-total"]["completedEvidence"]
    assert (total["requiredCredits"], total["matchedCredits"]) == (23, 12)
    assert result["cs-technical-total"]["completedStatus"] == "unsatisfied"
    assert result["cs-math-oriented"]["completedStatus"] == "satisfied"
