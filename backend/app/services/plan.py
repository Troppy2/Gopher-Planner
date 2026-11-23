"""Plan reads, validated saves and generation glue. The route only translates errors."""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import uuid4

from app.extensions import db
from app.repositories.catalog import find_courses
from app.repositories.locks import lock_user
from app.repositories.plans import find_plan, planned_courses, replace_planned_courses
from app.schemas.coursework import CODE_PATTERN
from app.services.coursework import get_coursework
from app.services.metadata import referenced_codes, resolve_course
from app.services.planning.eligibility import INFORMATIONAL
from app.services.planning.generate import CATEGORY_PRIORITY, STATUS_WARNINGS, generate_plan
from app.services.planning.terms import current_term, plan_window, term_index
from app.services.planning.validate import validate_plan
from app.services.programs import ProgramVersionUnavailable, ProgramVersionUnconfirmed, available_catalog_terms, load_program
from app.services.requirements import evaluate_program

NO_CREDIT = {"F", "N", "W", "I"}
LOCK_REASONS = {
    "course_metadata_unavailable": "Prerequisite information for this course is not available from the official catalog, so it cannot be scheduled automatically. Ask your advisor before planning it.",
    "catalog_metadata_conflict": "Official sources disagree about this course's details. Ask your advisor before planning it.",
}
UNSET = object()


def today():
    return date.today()


class PlanError(Exception):
    def __init__(self, status, code, message, violations=None):
        super().__init__(message)
        self.status, self.code, self.message, self.violations = status, code, message, violations


@dataclass
class Context:
    program: dict | None
    status: str
    catalog_term: str | None
    available: list = field(default_factory=list)


def resolve_context(user, requested=UNSET):
    major = user.major or ""
    if requested is UNSET:
        saved = find_plan(user.id)
        requested = saved.catalog_term if saved else None
    available = available_catalog_terms(major)
    try:
        program = load_program(major, requested)
    except ProgramVersionUnconfirmed:
        return Context(None, "unconfirmed", None, available)
    except ProgramVersionUnavailable:
        return Context(None, "unavailable", None, available)
    if program is None:
        return Context(None, "unknown", None, [])
    return Context(program, "ok", requested, available)


def expression_codes(node):
    if not isinstance(node, dict):
        return []
    if node.get("type") == "course":
        return [node.get("course_code")]
    return [code for child in node.get("requirements") or [] for code in expression_codes(child)]


def gather_metadata(program, codes, *, closure_depth=4):
    """Resolve each code once, following prerequisite references so generation can schedule them."""
    metadata, pending = {}, set(codes)
    for _ in range(closure_depth + 1):
        pending -= set(metadata)
        if not pending:
            break
        rows = find_courses(pending)
        found = {code: resolve_course(code, program, rows.get(code)) for code in pending}
        metadata.update(found)
        pending = {code for record in found.values() if record
                   for code in expression_codes(record["prerequisites"]["expression"])}
    return metadata


def window_terms(user):
    current = current_term(today())
    return current, plan_window(current, user.graduation_target or "")


def coursework_attempts(user):
    return [{"code": row["code"], "credits": row["credits"], "status": row["status"], "grade": row["grade"],
             "term": row["term"], "title": row["title"]} for row in get_coursework(user)["courses"]]


def locked_codes(attempts):
    """Done and in-progress codes; an in-progress attempt wins over earlier done attempts."""
    locked = {}
    for item in attempts:
        if locked.get(item["code"]) != "prog":
            locked[item["code"]] = item["status"]
    return locked


def categories(program):
    mapping = {}
    if not program:
        return mapping
    ordered = sorted(enumerate(program["groups"]), key=lambda pair: (CATEGORY_PRIORITY.get(pair[1]["category"], 9), pair[0]))
    def codes(node):
        if node["type"] == "course":
            yield node["code"]
        if node["type"] in {"credits", "count"}:
            yield from program["courseSets"][node["courseSet"]]["codes"]
        for child in node.get("children", []):
            yield from codes(child)

    for _, group in ordered:
        for code in codes(group["rule"]):
            mapping.setdefault(code, group["category"])
    return mapping


def earned(item):
    return item["status"] == "done" and item.get("grade") not in NO_CREDIT


def _best_row(rows):
    progress = [row for row in rows if row["status"] == "prog"]
    if progress:
        return progress[0]
    return max(rows, key=lambda row: (earned(row), term_index(row["term"]) if row["term"] else -1))


def build_plan(user, context, planned):
    """The full Plan wire object for one user, a resolved program version and a set of placements."""
    current, window = window_terms(user)
    terms = ["Completed", current, *window]
    attempts = coursework_attempts(user)
    program = context.program
    program_codes = referenced_codes(program) if program else set()
    rows_by_code = {}
    for item in attempts:
        rows_by_code.setdefault(item["code"], []).append(item)
    listed = program_codes | set(planned)
    metadata = gather_metadata(program, listed | set(rows_by_code))
    category = categories(program)
    courses = []
    for code in sorted(listed):
        record = metadata.get(code)
        row = _best_row(rows_by_code[code]) if code in rows_by_code else None
        course = {
            "code": code, "title": (record or {}).get("title") or (row or {}).get("title") or code,
            "credits": float((record or {}).get("minimumCredits") or 0), "requirement": category.get(code, "Elective"),
            "offered": list((record or {}).get("offered") or []),
            "prereqs": list(dict.fromkeys(expression_codes((record or {}).get("prerequisites", {}).get("expression")))),
            # The full tree, so clients never read flat display prereqs as all-required.
            "prerequisiteTree": (record or {}).get("prerequisites", {}).get("expression"),
            "concurrent": [], "professors": [], "term": None,
            "metadataSource": (record or {}).get("metadataSource", "catalog"),
            "metadataWarnings": list((record or {}).get("metadataWarnings", [])),
        }
        if row:
            course.update(status=row["status"], credits=float(row["credits"]),
                          term=current if row["status"] == "prog" else (row["term"] if row["term"] in terms else "Completed"))
        elif code in planned:
            course.update(status="plan", term=planned[code][0])
        elif record is None or record.get("blockedReason"):
            course.update(status="block", lockReason=LOCK_REASONS.get((record or {}).get("blockedReason"), LOCK_REASONS["course_metadata_unavailable"]))
        else:
            course["status"] = "avail"
        courses.append(course)
    base = 0.0
    for code, rows in rows_by_code.items():
        if code not in listed:
            base += max((float(row["credits"]) for row in rows if earned(row)), default=0.0)
    warnings = set()
    progress = []
    if context.status != "ok":
        warnings.add(STATUS_WARNINGS[context.status])
    planned_attempts = [{"code": code, "credits": float(metadata[code]["minimumCredits"]), "status": "plan", "grade": None, "term": term}
                        for code, (term, _) in planned.items() if metadata.get(code) and code not in rows_by_code]
    for item in planned_attempts:
        warnings.update(code for code in metadata[item["code"]]["metadataWarnings"] if code in INFORMATIONAL | {"catalog_metadata_conflict"})
    if program:
        evaluation = evaluate_program(program, [*attempts, *planned_attempts])
        progress = evaluation["requirementProgress"]
        warnings.update(evaluation["warnings"])
        listed_earned = sum(max((float(row["credits"]) for row in rows_by_code[code] if earned(row)), default=0.0)
                            for code in listed if code in rows_by_code)
        projected = base + listed_earned + sum(float(item["credits"]) for item in attempts if item["status"] == "prog") \
            + sum(item["credits"] for item in planned_attempts)
        if projected < float(program["totalCredits"]):
            warnings.add("graduation_target_unreachable")
    return {
        "terms": terms, "currentTerm": current, "baseCredits": base, "courses": courses,
        "catalogTerm": context.catalog_term, "availableCatalogTerms": context.available,
        "warnings": sorted(warnings), "requirementProgress": progress,
    }


def get_plan(user):
    return build_plan(user, resolve_context(user), planned_courses(user.id))


def parse_catalog_term(body):
    if "catalogTerm" not in body or body["catalogTerm"] is None:
        return UNSET
    if not isinstance(body["catalogTerm"], str):
        raise PlanError(400, "invalid_change", "catalogTerm must be a string")
    return body["catalogTerm"]


def confirmed(context):
    if context.status == "unconfirmed":
        raise PlanError(400, "program_version_unconfirmed", "Select a supported catalog term for your program")
    if context.status == "unavailable":
        raise PlanError(400, "program_version_unavailable", "That catalog term is not available for your program")
    return context


def save_changes(user, body):
    if not isinstance(body, dict) or set(body) - {"changes", "catalogTerm"} or not isinstance(body.get("changes"), list) \
            or len(body["changes"]) > 300:
        raise PlanError(400, "invalid_change", "Expected {changes: [...]} with at most 300 changes")
    requested = parse_catalog_term(body)
    _, window = window_terms(user)
    for change in body["changes"]:
        if not isinstance(change, dict) or set(change) != {"code", "status", "term"}:
            raise PlanError(400, "invalid_change", "Each change needs exactly code, status and term")
        if not isinstance(change["code"], str) or not CODE_PATTERN.fullmatch(change["code"]):
            raise PlanError(400, "invalid_change", "Invalid course code")
        if change["status"] == "plan":
            if change["term"] not in window:
                raise PlanError(400, "invalid_change", "Planned courses need a future term inside the plan window")
        elif change["status"] == "avail":
            if change["term"] is not None:
                raise PlanError(400, "invalid_change", "Removing a course requires term null")
        else:
            raise PlanError(400, "invalid_change", "status must be plan or avail")
    lock_user(user.id)  # held until commit: the read-modify-write below cannot interleave
    context = confirmed(resolve_context(user, requested))
    locked = locked_codes(coursework_attempts(user))
    planned = dict(planned_courses(user.id))
    changed = set()
    additions = {change["code"] for change in body["changes"] if change["status"] == "plan"
                 and change["code"] not in planned and change["code"] not in locked}
    metadata = gather_metadata(context.program, set(planned) | additions, closure_depth=0)
    for change in body["changes"]:
        code = change["code"]
        changed.add(code)
        if code in locked:
            continue
        if change["status"] == "plan":
            if code not in planned and metadata.get(code) is None:
                raise PlanError(404, "unknown_course", f"{code} is not in the catalog or your program")
            planned[code] = (change["term"], "user")
        else:
            planned.pop(code, None)
    violations = validate_plan({code: term for code, (term, _) in planned.items() if term in window},
                               locked=locked, metadata=metadata, terms=window, changed=changed)
    if violations:
        raise PlanError(409, "plan_invalid", "The resulting plan breaks a scheduling rule", violations)
    replace_planned_courses(user.id, planned, catalog_term=context.catalog_term, set_term=requested is not UNSET)
    db.session.commit()
    return get_plan(user)


def generate(user, body):
    """Synchronous generation. Dry runs and unconfirmed/unsupported versions write nothing."""
    if body is None:
        body = {}
    if not isinstance(body, dict) or set(body) - {"dryRun", "catalogTerm"} or not isinstance(body.get("dryRun", False), bool):
        raise PlanError(400, "invalid_request", "Expected {dryRun?: boolean, catalogTerm?: string}")
    requested = parse_catalog_term(body)
    dry_run = body.get("dryRun", False)
    context = resolve_context(user, requested)
    if context.status in {"unconfirmed", "unavailable"}:
        plan = build_plan(user, context, planned_courses(user.id))
        return {"jobId": str(uuid4()), "status": "succeeded", "warnings": plan["warnings"], "plan": plan}
    if not dry_run:
        lock_user(user.id)
    _, window = window_terms(user)
    attempts = coursework_attempts(user)
    program = context.program
    metadata = gather_metadata(program, referenced_codes(program)) if program else {}
    earned_base = sum(max((float(row["credits"]) for row in attempts if row["code"] == code and earned(row)), default=0.0)
                      for code in {item["code"] for item in attempts})
    result = generate_plan(program, coursework=[item for item in attempts if item["status"] in {"done", "prog"}], metadata=metadata,
                    terms=window, credit_load=user.credit_load, base_credits=earned_base,
                    status="ok" if program else "unknown")
    planned = {item["code"]: (item["term"], "generated") for item in result["placements"]}
    if not program:
        # Unknown programs keep any user-added catalog courses; nothing is generated for them.
        planned = {code: value for code, value in planned_courses(user.id).items() if value[1] == "user"}
    plan = build_plan(user, context, planned)
    warnings = sorted(set(plan["warnings"]) | set(result["warnings"]))
    plan["warnings"] = warnings
    if not dry_run:
        replace_planned_courses(user.id, planned, catalog_term=context.catalog_term, set_term=requested is not UNSET,
                                generated_at=datetime.now(timezone.utc))
        db.session.commit()
    return {"jobId": str(uuid4()), "status": "succeeded", "warnings": warnings, "plan": plan}
