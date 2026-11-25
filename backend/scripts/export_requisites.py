"""Export the enrollment requirements UMN registration enforces for each Twin Cities class section.

The course catalog often leaves prerequisites out of its text, or states them only in prose. Registration
enforces a requirement group per section; Schedule Builder publishes its text (for example
"NSci 2001 or 2101"). This exporter records that text per term and course, unparsed.

Sources, both public and unauthenticated:
- https://courses.umn.edu/campuses/umntc/terms/<term>/courses.json lists each subject's courses and section
  class numbers for a term.
- https://schedulebuilder.umn.edu/api.php?type=sections returns each section's enforced ``requirements``.

Requests are sequential with a pause between them. No login, token or student data is used.
"""
import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ["term", "strm", "code", "course_id", "requirement_group", "requirement_text", "sections", "source_url",
          "retrieved_at_utc"]
CLASS_SEARCH = "https://courses.umn.edu/campuses/umntc/terms/{strm}/courses.json"
SCHEDULE_BUILDER = "https://schedulebuilder.umn.edu/api.php"
BATCH = 100


def strm_term(strm):
    """PeopleSoft term code: 1 + two-digit year + season digit (3 Spring, 5 Summer, 9 Fall)."""
    strm = str(strm)
    season = {"3": "Spring", "5": "Summer", "9": "Fall"}[strm[-1]]
    return f"{season} 20{strm[1:3]}"


def requirement_rows(strm, sections, *, retrieved_at):
    """One row per (course, requirement group) across a term's sections; sections without one become a blank group."""
    grouped = {}
    for section in sections:
        code = f"{section['subject']} {section['catalog_nbr']}"
        requirements = section.get("requirements") or [{"id": "", "description": ""}]
        for requirement in requirements:
            key = (code, requirement.get("id") or "")
            row = grouped.setdefault(key, {
                "term": strm_term(strm), "strm": str(strm), "code": code, "course_id": str(section.get("crse_id") or ""),
                "requirement_group": requirement.get("id") or "",
                "requirement_text": " ".join((requirement.get("description") or "").split()),
                "sections": 0,
                "source_url": (f"https://schedulebuilder.umn.edu/explore/{section['subject']}/"
                               f"{section['catalog_nbr']}/{strm}/"),
                "retrieved_at_utc": retrieved_at})
            row["sections"] += 1
    return [grouped[key] for key in sorted(grouped)]


def class_numbers(session, strm, subject, pause):
    response = session.get(CLASS_SEARCH.format(strm=strm), params={"q": f"subject_id={subject}"}, timeout=120)
    time.sleep(pause)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return [section["class_number"] for course in response.json().get("courses", [])
            for section in course.get("sections", [])]


def fetch_sections(session, strm, numbers, pause):
    sections = []
    for start in range(0, len(numbers), BATCH):
        response = session.get(SCHEDULE_BUILDER, timeout=120, params={
            "type": "sections", "institution": "UMNTC", "campus": "UMNTC", "term": strm,
            "class_nbrs": ",".join(numbers[start:start + BATCH])})
        time.sleep(pause)
        response.raise_for_status()
        sections.extend(response.json())
    return sections


def subjects_from(courses_csv):
    csv.field_size_limit(100_000_000)
    with open(courses_csv, encoding="utf-8-sig", newline="") as source:
        return sorted({row["code"].split()[0] for row in csv.DictReader(source) if row["code"].strip()})


def main(argv=None):
    import requests

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New CSV path; existing snapshots are preserved")
    parser.add_argument("--terms", required=True, help="Comma-separated PeopleSoft term codes, for example 1269,1273")
    parser.add_argument("--courses", type=Path, required=True, help="Course export whose subject codes are queried")
    parser.add_argument("--pause", type=float, default=0.5, help="Seconds between requests")
    args = parser.parse_args(argv)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    subjects = subjects_from(args.courses)
    rows = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "course-planner-requisite-export"})
        for strm in [term.strip() for term in args.terms.split(",") if term.strip()]:
            numbers = []
            for subject in subjects:
                numbers.extend(class_numbers(session, strm, subject, args.pause))
            numbers = list(dict.fromkeys(numbers))
            sections = fetch_sections(session, strm, numbers, args.pause)
            rows.extend(requirement_rows(strm, sections, retrieved_at=retrieved_at))
            print(f"{strm_term(strm)}: {len(sections)} sections")
    if not rows:
        raise ValueError("Cannot publish an empty requisite snapshot")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} course requirement rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
