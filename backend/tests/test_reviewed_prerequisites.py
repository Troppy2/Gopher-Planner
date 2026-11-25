"""Integrity checks for the hand-reviewed prerequisite file and the requisite parser.

These check structure and sourcing, not academic truth: every tree validates, cites a source, names only
courses in the official course snapshot, and contains no prerequisite cycle the planner could never order."""
import csv
import json
from datetime import date
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "data"
REVIEWED = DATA / "prerequisites" / "reviewed.json"
COURSES = DATA / "catalog-exports" / "courses.2026-11-23.csv"


@pytest.fixture(scope="module")
def reviewed():
    return json.loads(REVIEWED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def catalog_codes():
    csv.field_size_limit(100_000_000)
    with COURSES.open(encoding="utf-8-sig", newline="") as source:
        return {" ".join(row["code"].split()) for row in csv.DictReader(source)}


def codes(node):
    if node is None or node["type"] == "condition":
        return set()
    if node["type"] == "course":
        return {node["course_code"]}
    return set().union(*(codes(child) for child in node["requirements"]))


def test_every_reviewed_tree_validates_and_cites_a_dated_source(reviewed):
    from app.schemas.programs import prerequisite_expression

    assert reviewed["courses"]
    for source in reviewed["sources"].values():
        assert source["url"].startswith("https://") and source["section"]
        date.fromisoformat(source["retrieved"])
    for code, entry in reviewed["courses"].items():
        assert entry["sourceRef"] in reviewed["sources"], code
        if entry["expression"] is not None:
            prerequisite_expression(entry["expression"])


def test_reviewed_trees_name_only_courses_in_the_official_snapshot(reviewed, catalog_codes):
    for code, entry in reviewed["courses"].items():
        assert code in catalog_codes
        assert codes(entry["expression"]) <= catalog_codes, code


def test_reviewed_trees_contain_no_prerequisite_cycles(reviewed):
    graph = {code: codes(entry["expression"]) for code, entry in reviewed["courses"].items()}
    state = {}

    def visit(code, path):
        if state.get(code) == "done":
            return
        assert state.get(code) != "active", " -> ".join(path + [code])
        state[code] = "active"
        for child in graph.get(code, ()):
            visit(child, path + [code])
        state[code] = "done"

    for code in graph:
        visit(code, [])


def test_requisite_parser_reads_registration_shorthand_and_refuses_prose():
    from app.services.requisites import parse_requisite

    subjects = {"MATH", "CSCI", "NSCI"}
    assert parse_requisite("NSci 2001 or 2101", subject="NSCI") == {"type": "any_of", "requirements": [
        {"type": "course", "course_code": "NSCI 2001"}, {"type": "course", "course_code": "NSCI 2101"}]}
    assert parse_requisite("[1272 or 1372] w/grade of at least C-", subject="MATH") == {"type": "all_of", "requirements": [
        {"type": "any_of", "requirements": [{"type": "course", "course_code": "MATH 1272"},
                                            {"type": "course", "course_code": "MATH 1372"}]},
        {"type": "condition", "text": "Minimum grade C-"}]}
    assert parse_requisite("CSCI [1103 OR 1113] & MATH 1271", subject="CSCI", subjects=subjects)["type"] == "all_of"
    concurrent = parse_requisite("concurrent registration is required (or allowed) in 2243", subject="MATH")
    assert concurrent == {"type": "course", "course_code": "MATH 2243", "concurrent": True}
    assert parse_requisite("Kin major or instr consent", subject="KIN")["type"] == "condition"
    # A word before a bracket is only a subject when it is a known subject code.
    assert parse_requisite("major (CSCI 1001)", subject="CSCI", subjects=subjects)["type"] == "condition"
    assert parse_requisite("None.") is None


def test_resolution_prefers_reviewed_then_enforced_then_catalog():
    from app.services.requisites import resolve_prerequisites

    enforced = {"TEST 3001": {"texts": ["TEST 1001 or 1002"]}, "TEST 3002": {"texts": ["Majors only"]}}
    reviewed = {"TEST 3001": {"expression": None, "sourceRef": "synthetic"}}
    known = {"TEST 1001", "TEST 1002", "TEST 1003"}
    assert resolve_prerequisites("TEST 3001", "TEST 1003", enforced=enforced, reviewed=reviewed, known=known)[:2] == (None, "reviewed")
    tree, origin, _ = resolve_prerequisites("TEST 3001", "TEST 1003", enforced=enforced, subject="TEST", known=known)
    assert origin == "enforced" and tree["type"] == "any_of"
    assert resolve_prerequisites("TEST 3003", "TEST 1003", known=known)[:2] == ({"type": "course", "course_code": "TEST 1003"}, "catalog")
    # Blank catalog text plus an enforced requirement never reads as "no prerequisites".
    tree, origin, _ = resolve_prerequisites("TEST 3002", "", enforced=enforced)
    assert origin == "enforced" and tree["type"] == "condition"
    # A required course missing from the catalog leaves the requirement as text instead of blocking forever.
    assert resolve_prerequisites("TEST 3004", "TEST 1001, GONE 1000", known=known)[0]["type"] == "condition"
