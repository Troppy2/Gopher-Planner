"""Parse the text of a UMN APAS degree audit into course rows.

APAS prints every course as one line in this shape:

    F 25 1CSCI1133 4.0 A Intro to Programming Concepts
    SP26 1PHYS1301W 4.0 A Phys for Sci and Engr I
    F 26 1CSCI2021 4.0 AF IP Machine Architecture and Org      <- in progress
    SP25 1MATH1271 4.0 T5 MATHHL APPLICATIONS&INTERPRET        <- IB / transfer
    IBCOURSE: MATHAPPINTHL                                     <- next line marks IB

We match only that line shape. Lines such as "Select from: 1CSCI 4041" are
requirement options, not courses taken, so they never match.

The same course appears in several audit sections; rows are de-duplicated by
(course code, term). This module has no Flask or database code so it can be
unit-tested on plain strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

SEASON_CODES = {"F": "Fall", "SP": "Spring", "S": "Spring", "SU": "Summer"}

# Grades that course_records accepts. Transfer grades such as T5 are stored as NULL.
VALID_GRADES = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F", "S", "N"}

COURSE_LINE = re.compile(
    r"^(?P<season>F|SP|SU|S)\s?(?P<year>\d{2})\s+"   # term: "F 25", "SP26"
    r"1(?P<subject>[A-Z]{2,4})\s*"                   # "1" = Twin Cities campus, then subject
    r"(?P<number>\d{4}[A-Z]?)\s+"                    # 1133, 1301W
    r"(?P<credits>\d+\.\d)\s+"                       # 4.0
    r"(?P<grade>[A-Z][A-Z+\-]?\d?)"                  # A, A-, S, T5, AF, SN
    r"(?P<in_progress>\s+IP)?"                       # " IP" = in progress
    r"\s+(?P<title>.+)$"
)
TRANSFER_MARKER = re.compile(r"^(IBCOURSE|APCOURSE|TRCOURSE):", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedCourse:
    course_code: str          # "CSCI 1133"
    title: str
    term_year: int            # 2025
    term_season: str          # "Fall"
    credits: Decimal
    grade: str | None         # None for in-progress and transfer credit
    status: str               # "completed" | "in_progress"
    credit_source: str        # "institutional" | "IB" | "AP" | "transfer"


def _credit_source(grade: str, next_line: str) -> str:
    marker = TRANSFER_MARKER.match(next_line.strip())
    if marker:
        return {"IBCOURSE": "IB", "APCOURSE": "AP"}.get(marker.group(1).upper(), "transfer")
    if grade.startswith("T"):
        return "transfer"
    return "institutional"


def parse_apas_text(text: str) -> list[ParsedCourse]:
    lines = text.splitlines()
    courses: dict[tuple[str, int, str], ParsedCourse] = {}

    for index, raw in enumerate(lines):
        match = COURSE_LINE.match(raw.strip())
        if match is None:
            continue

        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        grade = match["grade"]
        in_progress = match["in_progress"] is not None
        source = _credit_source(grade, next_line)

        course = ParsedCourse(
            course_code=f"{match['subject']} {match['number']}",
            title=match["title"].strip(),
            term_year=2000 + int(match["year"]),
            term_season=SEASON_CODES[match["season"]],
            credits=Decimal(match["credits"]),
            grade=None if in_progress or grade not in VALID_GRADES else grade,
            status="in_progress" if in_progress else "completed",
            credit_source=source,
        )
        courses.setdefault((course.course_code, course.term_year, course.term_season), course)

    return list(courses.values())


def extract_pdf_text(file_obj) -> str:
    """Return all text in a PDF. Returns "" for a scanned PDF with no text layer."""
    import pdfplumber

    with pdfplumber.open(file_obj) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
