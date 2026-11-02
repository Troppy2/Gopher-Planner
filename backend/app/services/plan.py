"""Build the frontend's Plan shape from course_records.

MVP scope: completed courses go in "Completed", in-progress courses go in the
current term, and future terms are listed but empty. Placing future courses
(plan generation) and saving edits (PUT /plan) come later.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from typing import Callable

from app.models import CourseRecord

COMPLETED = "Completed"
SEASON_ORDER = {"Spring": 1, "Summer": 2, "Fall": 3}
DEFAULT_FUTURE_TERMS = 7   # about four years including the current term


def term_label(season: str, year: int) -> str:
    return f"{season} {year}"


def current_term(records: list[CourseRecord], today: date) -> tuple[str, int]:
    """The term the student is taking classes in now."""
    in_progress = [r for r in records if r.status == "in_progress" and r.term_year]
    if in_progress:
        latest = max(in_progress, key=lambda r: (r.term_year, SEASON_ORDER[r.term_season]))
        return latest.term_season, latest.term_year
    # No in-progress rows: use the calendar. Summer counts toward the coming Fall.
    return ("Spring", today.year) if today.month <= 5 else ("Fall", today.year)


def next_term(season: str, year: int) -> tuple[str, int]:
    # Plans skip summer: Spring -> Fall -> next Spring.
    return ("Fall", year) if season == "Spring" else ("Spring", year + 1)


def parse_term(value: str | None) -> tuple[str, int] | None:
    match = re.fullmatch(r"\s*(Spring|Summer|Fall)\s+(\d{4})\s*", value or "")
    return (match[1], int(match[2])) if match else None


def plan_terms(start: tuple[str, int], graduation: tuple[str, int] | None) -> list[str]:
    terms = [term_label(*start)]
    season, year = start
    end_key = (graduation[1], SEASON_ORDER[graduation[0]]) if graduation else None
    while True:
        season, year = next_term(season, year)
        if end_key is None and len(terms) > DEFAULT_FUTURE_TERMS:
            break
        if end_key is not None and (year, SEASON_ORDER[season]) > end_key:
            break
        terms.append(term_label(season, year))
    return [COMPLETED] + terms


def requirement_for(code: str) -> str:
    # Placeholder until degree requirements are modeled: group by subject.
    subject = code.split()[0]
    if subject == "CSCI":
        return "Major core"
    if subject in ("MATH", "STAT"):
        return "Math and stats"
    return "Liberal ed"


def build_plan(
    records: list[CourseRecord],
    catalog_info: Callable[[list[str]], dict[str, dict]],
    graduation_target: str | None,
    today: date,
) -> dict:
    season, year = current_term(records, today)
    terms = plan_terms((season, year), parse_term(graduation_target))
    info = catalog_info([r.course_code for r in records if r.course_code])

    courses = []
    for r in records:
        if r.kind != "course":
            continue
        catalog = info.get(r.course_code, {})
        done = r.status == "completed"
        courses.append({
            "code": r.course_code,
            "title": r.title or catalog.get("title", ""),
            "credits": float(r.credits),
            "status": "done" if done else "prog",
            "requirement": requirement_for(r.course_code),
            "offered": catalog.get("offered", []),
            "prereqs": catalog.get("prereqs", []),
            "concurrent": [],
            "professors": [],
            "term": COMPLETED if done else term_label(r.term_season, r.term_year),
        })

    return {
        "terms": terms,
        "currentTerm": term_label(season, year),
        "baseCredits": 0,   # IB/AP/transfer credit is listed as courses instead
        "courses": courses,
    }


def read_catalog_info(connection: sqlite3.Connection, codes: list[str]) -> dict[str, dict]:
    """Title, offered terms and prerequisite codes for catalog courses."""
    if not codes:
        return {}
    marks = ",".join("?" for _ in codes)
    rows = connection.execute(
        f"SELECT id, course_code, course_name, typically_offered FROM courses "
        f"WHERE course_code IN ({marks})", codes,
    ).fetchall()
    info = {
        row["course_code"]: {
            "title": row["course_name"],
            "offered": [t for t in ("Fall", "Spring", "Summer") if t in (row["typically_offered"] or "")],
            "prereqs": [],
            "_id": row["id"],
        }
        for row in rows
    }
    by_id = {v["_id"]: code for code, v in info.items()}
    if by_id:
        id_marks = ",".join("?" for _ in by_id)
        for edge in connection.execute(
            f"SELECT e.course_id, c.course_code FROM prerequisite_edges e "
            f"JOIN courses c ON c.id = e.prerequisite_course_id "
            f"WHERE e.course_id IN ({id_marks})", list(by_id),
        ):
            info[by_id[edge[0]]]["prereqs"].append(edge[1])
    for value in info.values():
        value.pop("_id")
    return info
