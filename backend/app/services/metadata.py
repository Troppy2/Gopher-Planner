"""Version-aware course metadata selection across the read-only catalog and program supplements.

Precedence for a selected program version:
1. A catalog record whose release is mapped by the program's sourced ``catalogCompatibility``.
   If a matching supplemental record disagrees, both remain visible but placement is blocked.
2. Target-version supplemental metadata from the program file.
3. Unknown-version or unmapped legacy catalog facts, flagged ``catalog_version_unverified``.
"""
import copy
from collections import Counter
import re

SEASONS = ("Fall", "Spring", "Summer")
CODE = re.compile(r"^([A-Za-z]{2,6}) ?(\d{4}[A-Za-z]?)$")


RESTRICTED_TITLES = ("freshman seminar", "first-year seminar", "first year seminar", "talented youth")


def restricted_enrollment(code, title):
    """True for courses limited to a group the planner can't confirm a student belongs to: honors
    sections (an ``H`` suffix), freshman seminars, and the UM Talented Youth Mathematics Program."""
    if code.split(" ")[-1].endswith("H"):
        return True
    return any(marker in (title or "").lower() for marker in RESTRICTED_TITLES)


def normalize_code(code):
    match = CODE.match((code or "").strip())
    return f"{match.group(1).upper()} {match.group(2).upper()}" if match else code


def normalize_expression(node):
    if not isinstance(node, dict):
        return node
    node = dict(node)
    if node.get("type") == "course":
        node["course_code"] = normalize_code(node.get("course_code"))
    if isinstance(node.get("requirements"), list):
        node["requirements"] = [normalize_expression(child) for child in node["requirements"]]
    return node


def has_condition(node):
    if not isinstance(node, dict):
        return False
    return node.get("type") == "condition" or any(has_condition(child) for child in node.get("requirements") or [])


def parse_offered(text):
    """Return (seasons or None, verified). Legacy blanks and dashes are unknown, not every term."""
    if not text or text.strip() in {"-", ""}:
        return None, False
    seasons = [season for season in SEASONS if season in text]
    if not seasons:
        return None, False
    return seasons, text.strip().startswith("Every")


def _catalog_prerequisites(row):
    record = row.get("prerequisiteJson")
    if not isinstance(record, dict):
        return {"state": "unknown", "expression": None}
    tree = record.get("requirements")
    if record.get("status") == "none" and tree is None:
        return {"state": "verified_none", "expression": None}
    if record.get("status") == "found" and tree:
        return {"state": "tree", "expression": normalize_expression(tree)}
    return {"state": "unknown", "expression": None}


def _supplement_prerequisites(record):
    prerequisites = record["prerequisites"]
    if prerequisites is None:
        return {"state": "unknown", "expression": None}
    if prerequisites["expression"] is None:
        return {"state": "verified_none", "expression": None}
    return {"state": "tree", "expression": copy.deepcopy(prerequisites["expression"])}


def _from_catalog(code, row):
    offered, verified = parse_offered(row.get("typicallyOffered"))
    return {
        "code": code, "title": row["title"], "minimumCredits": row["minimumCredits"], "maximumCredits": row["maximumCredits"],
        "offered": offered, "offeredVerified": verified, "prerequisites": _catalog_prerequisites(row),
        "unresolved": list(row.get("unresolvedPrerequisites") or []), "metadataSource": "catalog",
    }


def _from_supplement(code, record):
    return {
        "code": code, "title": record["title"], "minimumCredits": record["minimumCredits"],
        "maximumCredits": record["maximumCredits"], "offered": list(record["offered"]) if record["offered"] else None,
        "offeredVerified": record["offered"] is not None, "prerequisites": _supplement_prerequisites(record),
        "unresolved": [], "metadataSource": "program",
    }


def _facts(value):
    return (value["title"], float(value["minimumCredits"]), float(value["maximumCredits"]),
            tuple(value["offered"] or ()), value["prerequisites"]["state"], repr(value["prerequisites"]["expression"]))


def resolve_course(code, program, catalog_row):
    """Return display and scheduling metadata for one course, or None when no source knows it."""
    supplement = (program or {}).get("courseMetadata", {}).get(code)
    versions = {mapping["catalogVersion"] for mapping in (program or {}).get("catalogCompatibility", [])}
    compatible = catalog_row is not None and catalog_row.get("catalogVersion") in versions
    warnings, blocked = [], None
    if compatible:
        result = _from_catalog(code, catalog_row)
        if supplement is not None and _facts(result) != _facts(_from_supplement(code, supplement)):
            warnings.append("catalog_metadata_conflict")
            blocked = "catalog_metadata_conflict"
    elif supplement is not None:
        result = _from_supplement(code, supplement)
    elif catalog_row is not None:
        result = _from_catalog(code, catalog_row)
        warnings.append("catalog_version_unverified")
    else:
        return None
    verified_offering = result.pop("offeredVerified")
    unresolved = result.pop("unresolved")
    if result["offered"] is None or not verified_offering:
        warnings.append("offered_terms_unverified")
    if result["prerequisites"]["state"] == "unknown":
        warnings.append("course_metadata_unavailable")
        blocked = blocked or "course_metadata_unavailable"
    elif unresolved or has_condition(result["prerequisites"]["expression"]):
        warnings.append("prerequisites_require_review")
    result["metadataWarnings"] = warnings
    result["blockedReason"] = blocked
    return result


def home_subject(program):
    """Most common subject among courses named directly in the program's rules, or None."""
    subjects = Counter()

    def walk(node):
        if node["type"] == "course":
            subjects[node["code"].split(" ")[0]] += 1
        for child in node.get("children", []):
            walk(child)

    for group in program["groups"]:
        walk(group["rule"])
    return subjects.most_common(1)[0][0] if subjects else None


def referenced_codes(program):
    codes = set()

    def walk(rule):
        if rule["type"] == "course":
            codes.add(rule["code"])
        for child in rule.get("children", []):
            walk(child)

    for group in program["groups"]:
        walk(group["rule"])
    for course_set in program["courseSets"].values():
        codes.update(course_set["codes"])
    return codes


def coverage_gaps(program, *, catalog_codes):
    """Referenced courses with no authoritative title and credits in either source."""
    return sorted(code for code in referenced_codes(program)
                  if code not in program["courseMetadata"] and code not in catalog_codes)


# Program-declared alternatives, which the catalog's prerequisite lists often leave out.

MAX_EQUIVALENT_SET = 8


def _number(code):
    """The digits of a course number: MATH 1571H is 1571."""
    return re.sub(r"\D", "", code.partition(" ")[2])


def _variants(codes):
    """Whether a set of courses are variants of one course rather than a menu of different ones."""
    numbers = {_number(code) for code in codes}
    if len(numbers) == 1:  # honors or suffix twins and cross-listings share a number
        return True
    levels = {number[:1] for number in numbers}
    return len(levels) == 1 and levels <= {"1", "2"}


def program_equivalents(program):
    """Courses a program treats as interchangeable, as ``code -> {code and its equivalents}``.

    Two shapes declare equivalence: a course set capped at one course (``count`` with ``maxCourses:
    1``, such as "one of MATH 1372, 1272, 1572H, 1472"), and an ``any`` rule whose options are all
    single courses (CSCI 1133 or CSCI 1133H). Larger sets are elective pools, not equivalents.

    A "choose one" list is often a menu of different courses ("one writing-intensive course: CSCI
    3081W, 4271W, ..."), and treating it as interchangeable lets a course satisfy a prerequisite with
    an unrelated one. So a group only counts when it is a set of variants: honors or suffix twins
    (CSCI 1133, 1133H), cross-listings (BA 2021, IBUS 2021), or lower-division courses at one level
    (MATH 1271, 1371, 1571H; PHYS 1221, 1301W).
    """
    groups = []

    def walk(node):
        if node["type"] == "count" and node.get("maxCourses") == 1:
            codes = program["courseSets"][node["courseSet"]]["codes"]
            if 1 < len(codes) <= MAX_EQUIVALENT_SET:
                groups.append(set(codes))
        if node["type"] == "any" and len(node["children"]) > 1 and all(child["type"] == "course" for child in node["children"]):
            groups.append({child["code"] for child in node["children"]})
        for child in node.get("children", []):
            walk(child)

    for group in program["groups"]:
        walk(group["rule"])
    equivalents = {}
    for group in filter(_variants, groups):
        for code in group:
            equivalents.setdefault(code, set()).update(group)
    return equivalents


def with_equivalents(expression, equivalents, *, owner=None):
    """A prerequisite expression where each listed course also accepts its program equivalents.

    ``owner`` is the course the expression belongs to; it never counts toward its own prerequisite."""
    if not isinstance(expression, dict):
        return expression
    if expression.get("type") == "course":
        code = expression.get("course_code")
        options = [code, *sorted(equivalents.get(code, set()) - {code, owner})]
        if len(options) == 1:
            return expression
        # Each equivalent keeps the original's timing: a concurrent prerequisite stays concurrent.
        extra = {"concurrent": True} if expression.get("concurrent") else {}
        return {"type": "any_of", "requirements": [{"type": "course", "course_code": option, **extra} for option in options]}
    if expression.get("type") in {"any_of", "all_of"}:
        return {**expression, "requirements": [with_equivalents(child, equivalents, owner=owner)
                                                for child in expression.get("requirements") or []]}
    return expression


def apply_equivalents(metadata, program):
    """Copies of resolved records whose prerequisites accept the program's equivalent courses."""
    equivalents = program_equivalents(program) if program else {}
    if not equivalents:
        return metadata
    updated = {}
    for code, record in metadata.items():
        prerequisites = (record or {}).get("prerequisites") or {}
        expression = prerequisites.get("expression")
        expanded = with_equivalents(expression, equivalents, owner=code)
        if record and expanded is not expression and expanded != expression:
            record = {**record, "prerequisites": {**prerequisites, "expression": expanded}}
        updated[code] = record
    return updated
