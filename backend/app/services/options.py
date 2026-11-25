"""Selectable profile options for onboarding and Settings."""
from datetime import date

from sqlalchemy import select

from app.extensions import db
from app.models import CatalogCourse
from app.services.planning.terms import current_term, future_terms
from app.services.programs import list_programs

STANDINGS = ["Freshman", "Sophomore", "Junior", "Senior"]

# Twelve future terms matches the planner's maximum plan window.
GRADUATION_TARGET_TERMS = 12

# Career suggestions carried over from the frontend mock. Majors without an entry get no
# suggestions; nothing is inferred for them.
CAREERS = {
    "Computer Science B.S.": [
        "Software engineer",
        "Full-stack developer",
        "Backend engineer",
        "Machine learning engineer",
        "Security engineer",
        "Product manager",
        "Graduate school (research)",
    ],
    "Computer Engineering B.S.": [
        "Embedded systems engineer",
        "Hardware design engineer",
        "Firmware engineer",
        "Robotics engineer",
        "Network engineer",
        "Graduate school (research)",
    ],
    "Data Science B.S.": [
        "Data scientist",
        "Data analyst",
        "Machine learning engineer",
        "Data engineer",
        "Business intelligence analyst",
        "Graduate school (research)",
    ],
}


def today():
    return date.today()


def catalog_subjects():
    rows = db.session.scalars(select(CatalogCourse.subject_code).distinct())
    return sorted({subject.strip().upper() for subject in rows if subject and subject.strip()})


def get_options():
    programs = list_programs()
    majors = [program["name"] for program in programs]
    return {
        "majors": majors,
        "unverifiedMajors": [program["name"] for program in programs if not program["reviewed"]],
        "standings": list(STANDINGS),
        "graduationTargets": future_terms(current_term(today()), GRADUATION_TARGET_TERMS),
        "subjects": catalog_subjects(),
        "careers": {major: list(CAREERS[major]) for major in majors if major in CAREERS},
    }
