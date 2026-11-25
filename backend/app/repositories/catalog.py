"""Read-only catalog queries against the application database. Only the importer writes these tables."""
import json

from sqlalchemy import Float, and_, cast, func, or_, select
from sqlalchemy.orm import aliased

from app.extensions import db
from app.models import CatalogCourse, CatalogPrerequisiteEdge, CatalogRelease
from app.services.metadata import restricted_enrollment


def _json(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def find_courses(codes):
    """Return catalog records by course code, including the catalog release version."""
    codes = sorted(set(codes))
    if not codes:
        return {}
    records = {}
    for start in range(0, len(codes), 500):
        rows = db.session.execute(
            select(CatalogCourse, CatalogRelease.version)
            .join(CatalogRelease, CatalogRelease.id == CatalogCourse.release_id)
            .where(CatalogCourse.course_code.in_(codes[start:start + 500])))
        for course, version in rows:
            records[course.course_code] = {
                "code": course.course_code, "title": course.course_name,
                "minimumCredits": float(course.minimum_credits), "maximumCredits": float(course.maximum_credits),
                "typicallyOffered": course.typically_offered, "catalogVersion": version,
                "prerequisiteJson": _json(course.prerequisite_json),
                "unresolvedPrerequisites": _json(course.prerequisite_unresolved_courses) or [],
            }
    return records


def course_exists(code):
    return db.session.scalar(select(CatalogCourse.id).where(CatalogCourse.course_code == code).limit(1)) is not None


def _credits(column):
    return cast(column, Float)


def search_courses(*, query="", subject="", level="", credits="", term="", requirement="", le="",
                   availability="", next_term="Spring", limit=50, offset=0):
    """Filtered, stably ordered catalog page. Text matching is case-insensitive on every database."""
    where = []
    for category in ([le] if isinstance(le, str) and le else le or []):
        designations = ";" + func.replace(CatalogCourse.le_attributes, "; ", ";") + ";"
        where.append(designations.contains(f";{category};", autoescape=True))
    if query:
        pattern = f"%{query}%"
        where.append(or_(CatalogCourse.course_code.ilike(pattern), CatalogCourse.course_name.ilike(pattern),
                         CatalogCourse.description.ilike(pattern)))
    if subject:
        where.append(CatalogCourse.subject_code == subject)
    if level:
        where.append(func.substr(CatalogCourse.course_number, 1, 1) == level)
    if credits == "1 to 2":
        where.append(_credits(CatalogCourse.maximum_credits) <= 2)
    elif credits == "3":
        where.append(and_(_credits(CatalogCourse.minimum_credits) == 3, _credits(CatalogCourse.maximum_credits) == 3))
    elif credits == "4 or more":
        where.append(_credits(CatalogCourse.minimum_credits) >= 4)
    if term:
        # Includes both regular and periodic offerings for that term.
        where.append(CatalogCourse.typically_offered.like(f"%{term}%"))
    if requirement:
        if requirement.lower() in {"none", "-"}:
            where.append(CatalogCourse.requirements == "-")
        else:
            where.append(CatalogCourse.requirements == requirement)
    if availability:
        # Matches the frontend's Spring default; alternating-year offerings need year-aware logic.
        offered = CatalogCourse.typically_offered.like(f"%{next_term}%")
        where.append(~offered if availability == "Not offered next term" else offered)
        where.append(CatalogCourse.typically_offered != "-")

    total = db.session.scalar(select(func.count()).select_from(CatalogCourse).where(*where))
    rows = db.session.scalars(
        select(CatalogCourse).where(*where)
        .order_by(CatalogCourse.subject_code, CatalogCourse.course_number, CatalogCourse.course_code)
        .limit(limit).offset(offset)).all()
    return rows, total


def get_course(code):
    return db.session.scalar(select(CatalogCourse).where(CatalogCourse.course_code == code).limit(1))


def resolved_prerequisites(course_id):
    prerequisite = aliased(CatalogCourse)
    return db.session.execute(
        select(prerequisite.course_code, prerequisite.course_name)
        .join(CatalogPrerequisiteEdge, CatalogPrerequisiteEdge.prerequisite_course_id == prerequisite.id)
        .where(CatalogPrerequisiteEdge.course_id == course_id)
        .order_by(prerequisite.course_code)).all()


def _le(value):
    return {part.strip() for part in (value or "").split(";") if part.strip()}


def open_to_any_undergraduate(code, title):
    """False for courses whose enrollment is restricted in ways the planner can't check for a student
    (see ``restricted_enrollment``) and for graduate-level (5xxx and above) courses."""
    number = code.split(" ")[-1]
    if number[:1].isdigit() and int(number[0]) >= 5:
        return False
    return not restricted_enrollment(code, title)


def _offered_every(offered):
    return (offered or "").strip().startswith("Every")


def le_designations(codes):
    """Catalog designation names per course code; codes missing from the catalog are omitted."""
    codes = sorted(set(codes))
    found = {}
    for start in range(0, len(codes), 500):
        rows = db.session.execute(select(CatalogCourse.course_code, CatalogCourse.le_attributes)
                                  .where(CatalogCourse.course_code.in_(codes[start:start + 500])))
        for code, value in rows:
            found[code] = found.get(code, set()) | _le(value)
    return found


def double_dippers(wanted, *, exclude, limit, offset):
    """Catalog courses carrying at least two of ``wanted`` groups of designations.

    ``wanted`` maps a need (for example "Literature") to the designation names that satisfy it.
    Returns (page of (course, covered needs), total). Most needs covered first, then courses open to
    any undergraduate, courses without prerequisites, lower levels, and code."""
    names = sorted({name for group in wanted.values() for name in group})
    if len(wanted) < 2 or not names:
        return [], 0
    rows = db.session.scalars(select(CatalogCourse).where(or_(*(CatalogCourse.le_attributes.contains(name) for name in names))))
    matches = []
    for course in rows:
        if course.course_code in exclude:
            continue
        carried = _le(course.le_attributes)
        covered = [need for need, group in wanted.items() if carried & set(group)]
        if len(covered) >= 2:
            number = course.course_number[:1]
            key = (-len(covered), not open_to_any_undergraduate(course.course_code, course.course_name),
                   course.prerequisite_status != "none", int(number) if number.isdigit() else 9, course.course_code)
            matches.append((key, course, covered))
    matches.sort(key=lambda match: match[0])
    return [(course, covered) for _, course, covered in matches[offset:offset + limit]], len(matches)


def le_candidates(needs, *, exclude, per_need=8):
    """Prerequisite-free courses any undergraduate can take, for open liberal education needs, as
    ``[(code, designations)]``.

    ``needs`` is ``[(label, designations)]``. For each need, keeps the ``per_need`` courses that cover
    the most open needs overall, then courses offered every year, lower levels, and code; the union is
    the generator's pool."""
    names = sorted({name for _, group in needs for name in group})
    if not names:
        return []
    rows = db.session.execute(
        select(CatalogCourse.course_code, CatalogCourse.le_attributes, CatalogCourse.course_name,
               CatalogCourse.typically_offered)
        .where(or_(*(CatalogCourse.le_attributes.contains(name) for name in names)))
        .where(CatalogCourse.prerequisite_status == "none")
        .where(CatalogCourse.typically_offered != "-"))
    scored = []
    for code, attributes, title, offered in rows:
        if code in exclude or not open_to_any_undergraduate(code, title):
            continue
        carried = _le(attributes)
        hits = sum(bool(carried & group) for _, group in needs)
        if hits:
            number = code.split(" ")[-1]
            scored.append(((-hits, not _offered_every(offered), int(number[0]) if number[:1].isdigit() else 9, code),
                           code, carried))
    scored.sort(key=lambda row: row[0])
    pool = {}
    for _, group in needs:
        for _, code, carried in [row for row in scored if row[2] & group][:per_need]:
            pool[code] = carried
    return sorted(pool.items())


def le_coverage(codes):
    """Liberal education designations carried by any of ``codes``."""
    codes = sorted(set(codes))
    if not codes:
        return set()
    covered = set()
    for value in db.session.scalars(select(CatalogCourse.le_attributes).where(CatalogCourse.course_code.in_(codes))):
        covered |= _le(value)
    return covered


def suggest_le_course(categories, *, season, exclude, bonus=()):
    """A prerequisite-free course any undergraduate can take, offered in ``season``, that covers the most
    of ``categories``.

    Ties prefer courses that also carry more ``bonus`` designations (other liberal education needs
    still open), then courses offered every year, then lower course levels, then code. Returns
    (code, covered categories) or None."""
    bonus = set(bonus)
    wanted = set(categories)
    if not wanted:
        return None
    rows = db.session.execute(
        select(CatalogCourse.course_code, CatalogCourse.le_attributes, CatalogCourse.typically_offered,
               CatalogCourse.course_name)
        .where(or_(*(CatalogCourse.le_attributes.contains(category) for category in sorted(wanted))))
        .where(CatalogCourse.prerequisite_status == "none"))
    best = None
    for code, attributes, offered, title in rows:
        if code in exclude or season not in (offered or "") or not open_to_any_undergraduate(code, title):
            continue
        covered = sorted(wanted & _le(attributes))
        if not covered:
            continue
        number = code.split(" ")[-1]
        key = (-len(covered), -len((bonus - set(covered)) & _le(attributes)), not _offered_every(offered),
               int(number[0]) if number[:1].isdigit() else 9, code)
        if best is None or key < best[0]:
            best = (key, code, covered)
    return (best[1], best[2]) if best else None
