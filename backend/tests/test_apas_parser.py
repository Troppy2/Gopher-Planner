"""APAS line parsing, checked on a made-up audit (no real student data)."""

from decimal import Decimal

from app.parsers.apas import parse_apas_text

SAMPLE = """\
Doe, Jane
Computer Science 2nd Major (BA)
Term Course Credit Grade Title
F 25 1CSCI1133 4.0 A Intro to Programming Concepts
F 25 1CSCI1135 1.0 S Exploring CSCI: Python
SP26 1PHYS1301W 4.0 B+ Phys for Sci and Engr I
F 26 1CSCI2021 4.0 AF IP Machine Architecture and Org
F 26 1CLA 1007 1.0 SN IP CLA 1st Yr Exper: Make-up
SP25 1MATH1271 4.0 T5 MATHHL APPLICATIONS&INTERPRET
IBCOURSE: MATHAPPINTHL
Select from: 1CSCI 3081W 1MADR 3081W
Select from: 1CSCI 4041 1MADR 4041
Courses Not Used in This Program
F 25 1CSCI1133 4.0 A Intro to Programming Concepts
"""


def by_code():
    return {c.course_code: c for c in parse_apas_text(SAMPLE)}


def test_finds_each_course_once():
    # CSCI 1133 is printed twice but counted once; "Select from" lines are ignored.
    assert sorted(by_code()) == [
        "CLA 1007", "CSCI 1133", "CSCI 1135", "CSCI 2021", "MATH 1271", "PHYS 1301W",
    ]


def test_completed_course():
    c = by_code()["CSCI 1133"]
    assert (c.term_season, c.term_year) == ("Fall", 2025)
    assert c.credits == Decimal("4.0")
    assert (c.grade, c.status, c.credit_source) == ("A", "completed", "institutional")
    assert c.title == "Intro to Programming Concepts"


def test_spring_term_without_space_and_writing_suffix():
    c = by_code()["PHYS 1301W"]
    assert (c.term_season, c.term_year, c.grade) == ("Spring", 2026, "B+")


def test_in_progress_has_no_grade():
    for code in ("CSCI 2021", "CLA 1007"):
        c = by_code()[code]
        assert (c.status, c.grade) == ("in_progress", None)


def test_ib_credit():
    c = by_code()["MATH 1271"]
    assert (c.credit_source, c.grade, c.status) == ("IB", None, "completed")


def test_text_that_is_not_an_audit():
    assert parse_apas_text("Hello, this is a cover letter.") == []
