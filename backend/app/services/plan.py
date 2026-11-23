"""Plan reads, validated saves and generation glue. The route only translates errors."""
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import uuid4
import math
from sqlalchemy import select

from app.extensions import db
from app.models import Coursework
from app.repositories.catalog import find_courses, le_coverage, suggest_le_course
from app.repositories.locks import lock_user
from app.repositories.plans import find_plan, planned_courses, planned_slots, replace_planned_courses
from app.schemas.coursework import CODE_PATTERN
from app.services.coursework import get_coursework
from app.services.metadata import referenced_codes, resolve_course
from app.services.planning.eligibility import INFORMATIONAL, placement_check
from app.services.planning.generate import CATEGORY_PRIORITY, STATUS_WARNINGS, generate_plan
from app.services.planning.sample import load_sample_plan
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
        if item["status"] == "done" and item.get("grade") in NO_CREDIT:
            continue
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


def slot_categories(program):
    sample = load_sample_plan(program["id"]) if program else None
    return {item.get("label") or ", ".join(item["categories"]): item["categories"]
            for term in (sample or {}).get("terms", []) for item in term["items"] if item["kind"] == "le"}


def audit_le_status(user_id):
    """(required, covered) liberal education categories from the newest parsed APAS upload, or None."""
    from app.models import Transcript

    row = db.session.scalars(select(Transcript).where(Transcript.user_id == user_id, Transcript.status == "parsed",
                                                      Transcript.le_required.is_not(None))
                             .order_by(Transcript.created_at.desc()).limit(1)).first()
    if row is None:
        return None
    return set(json.loads(row.le_required)), set(json.loads(row.le_covered or "[]"))


def generation_snapshot(user):
    saved = find_plan(user.id)
    return (user.major, user.graduation_target, user.credit_load, coursework_attempts(user),
            planned_courses(user.id), planned_slots(user.id), saved.catalog_term if saved else None)


def _best_row(rows):
    progress = [row for row in rows if row["status"] == "prog"]
    if progress:
        return progress[0]
    return max(rows, key=lambda row: (earned(row), term_index(row["term"]) if row["term"] else -1))


def build_plan(user, context, planned, *, slots=None):
    """The full Plan wire object for one user, a resolved program version and a set of placements."""
    current, window = window_terms(user)
    terms = ["Completed", current, *window]
    attempts = coursework_attempts(user)
    slots = planned_slots(user.id) if slots is None else slots
    program = context.program
    labels = slot_categories(program)
    program_codes = referenced_codes(program) if program else set()
    rows_by_code = {}
    for item in attempts:
        rows_by_code.setdefault(item["code"], []).append(item)
    listed = program_codes | set(planned) | {item["code"] for item in attempts if item["status"] == "prog"}
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
            "slot": slots.get(code) if code in planned else None,
            "slotCategories": sorted(set(labels.get(slots.get(code), [])) & le_coverage([code])) if slots.get(code) and code in planned else [],
            "metadataSource": (record or {}).get("metadataSource", "catalog"),
            "metadataWarnings": list((record or {}).get("metadataWarnings", [])),
        }
        if row and (code not in planned or earned(row) or row["status"] == "prog"):
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
    elective_credits = 0.0
    if context.status != "ok":
        warnings.add(STATUS_WARNINGS[context.status])
    planned_attempts = [{"code": code, "credits": float(metadata[code]["minimumCredits"]), "status": "plan", "grade": None, "term": term}
                        for code, (term, _) in planned.items() if metadata.get(code)
                        and not any(earned(row) or row["status"] == "prog" for row in rows_by_code.get(code, []))]
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
        elective_credits = max(0.0, float(program["totalCredits"]) - projected)
    return {
        "terms": terms, "currentTerm": current, "baseCredits": base, "courses": courses,
        "catalogTerm": context.catalog_term, "availableCatalogTerms": context.available,
        "warnings": sorted(warnings), "requirementProgress": progress,
        "electiveCredits": elective_credits,
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
    current, window = window_terms(user)
    for change in body["changes"]:
        if not isinstance(change, dict) or not {"code", "status", "term"} <= set(change) or set(change) - {"code", "status", "term", "slot", "credits"}:
            raise PlanError(400, "invalid_change", "Each change needs exactly code, status and term")
        if not isinstance(change["code"], str) or not CODE_PATTERN.fullmatch(change["code"]):
            raise PlanError(400, "invalid_change", "Invalid course code")
        if "credits" in change and (change["status"] != "prog" or isinstance(change["credits"], bool)
                or not isinstance(change["credits"], (int, float)) or not math.isfinite(change["credits"])
                or not 0.5 <= change["credits"] <= 12 or change["credits"] * 2 != int(change["credits"] * 2)):
            raise PlanError(400, "invalid_change", "Current course credits must be between 0.5 and 12 in half-credit increments")
        if change["status"] == "prog":
            if change["term"] != current:
                raise PlanError(400, "invalid_change", "In-progress courses belong in the current term")
        elif change["status"] == "plan":
            if change["term"] not in [current, *window]:
                raise PlanError(400, "invalid_change", "Planned courses need the current or a future term inside the plan window")
        elif change["status"] == "avail":
            if change["term"] is not None:
                raise PlanError(400, "invalid_change", "Removing a course requires term null")
        else:
            raise PlanError(400, "invalid_change", "status must be plan, prog or avail")
    lock_user(user.id)  # held until commit: the read-modify-write below cannot interleave
    context = resolve_context(user, requested)
    if requested is not UNSET or not body["changes"] or any(c["status"] == "plan" for c in body["changes"]):
        context = confirmed(context)
    slots = planned_slots(user.id)
    labels = slot_categories(context.program)
    removed = {c["code"] for c in body["changes"] if c["status"] == "avail"}
    replacing = {}
    for code in removed:
        if code in slots:
            replacing.setdefault(slots[code], set()).update(set(labels.get(slots[code], [])) & le_coverage([code]))
    attempts = coursework_attempts(user)
    locked = locked_codes(attempts)
    progress = {code for code, status in locked.items() if status == "prog"}
    touched = {change["code"] for change in body["changes"]}
    for code in progress & touched:
        locked.pop(code)
    locked.update({item["code"]: "done" for item in attempts if earned(item)})
    planned = dict(planned_courses(user.id))
    changed = set()
    additions = {change["code"] for change in body["changes"] if change["status"] in {"plan", "prog"}
                 and change["code"] not in planned and change["code"] not in locked}
    metadata = gather_metadata(context.program, set(planned) | additions, closure_depth=0)
    for change in body["changes"]:
        code = change["code"]
        if "slot" in change:
            label = change["slot"]
            if not isinstance(label, str) or label not in labels or change["status"] != "plan" \
                    or not set(labels[label]).intersection(le_coverage([code])):
                raise PlanError(400, "invalid_change", "The course must cover the sample-plan slot categories")
            slots[code] = label
        changed.add(code)
        if code in locked:
            continue
        if change["status"] == "prog":
            old = next((item for item in attempts if item["code"] == code and item["status"] == "prog"), None)
            record = metadata.get(code)
            if old is None and any(item["code"] == code and item["status"] == "done" and item["term"] == current for item in attempts):
                raise PlanError(409, "coursework_conflict", "An attempt for this course already exists in the current semester. Edit it in Your courses.")
            if old is None and record is None:
                raise PlanError(404, "unknown_course", "The current course is not in your coursework or catalog")
            if old is None:
                check = placement_check(record, current, 0, done={item["code"] for item in attempts if earned(item)},
                    in_progress=set(), planned={})
                if not check.ok:
                    raise PlanError(409, "plan_invalid", "This course cannot be added to the current semester", [
                        {"code": code, "reason": check.reason, "detail": check.detail}])
            planned.pop(code, None)
            locked[code] = "prog"
            changed.discard(code)
        elif change["status"] == "plan":
            if code not in planned and metadata.get(code) is None:
                raise PlanError(404, "unknown_course", f"{code} is not in the catalog or your program")
            planned[code] = (change["term"], "user")
        else:
            planned.pop(code, None)
    for label in {c["slot"] for c in body["changes"] if "slot" in c}:
        codes = [code for code in planned if slots.get(code) == label]
        if not replacing.get(label, set()) <= le_coverage(codes):
            raise PlanError(400, "invalid_change", "The replacement courses must preserve the slot categories")
    scheduling_terms = [current, *window]
    violations = validate_plan({code: term for code, (term, _) in planned.items() if term in scheduling_terms},
                               locked=locked, metadata=metadata, terms=scheduling_terms, changed=changed, current_term=current)
    if violations:
        raise PlanError(409, "plan_invalid", "The resulting plan breaks a scheduling rule", violations)
    # Enrollment edits and plan moves commit together. Failed validation leaves both unchanged.
    for change in body["changes"]:
        code = change["code"]
        if any(item["code"] == code and earned(item) for item in attempts):
            continue
        enrolled = db.session.scalars(select(Coursework).where(Coursework.user_id == user.id,
            Coursework.code == code, Coursework.status == "prog")).all()
        if change["status"] == "prog":
            row = enrolled[0] if enrolled else Coursework(user_id=user.id, code=code, source="manual", grade=None)
            record = metadata.get(code) or {}
            row.title = row.title or record.get("title") or code
            row.credits = change.get("credits", float(row.credits) if row.credits is not None else record.get("minimumCredits", 3))
            row.term, row.status = current, "prog"
            db.session.add(row)
            for duplicate in enrolled[1:]:
                db.session.delete(duplicate)
        else:
            for row in enrolled:
                db.session.delete(row)
    replace_planned_courses(user.id, planned, slots=slots, catalog_term=context.catalog_term, set_term=requested is not UNSET)
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
    snapshot = generation_snapshot(user)
    context = resolve_context(user, requested)
    if context.status in {"unconfirmed", "unavailable"}:
        plan = build_plan(user, context, planned_courses(user.id))
        return {"jobId": str(uuid4()), "status": "succeeded", "warnings": plan["warnings"], "plan": plan}
    current, window = window_terms(user)
    attempts = snapshot[3]
    if not any(item["status"] == "prog" for item in attempts):
        window = [current, *window]
    program = context.program
    sample = load_sample_plan(program["id"]) if program else None
    items = [item for term in (sample or {}).get("terms", []) for item in term["items"]]
    sample_codes = {code for item in items for code in item.get("codes", [])}
    metadata = gather_metadata(program, referenced_codes(program) | sample_codes) if program else {}
    covered = le_coverage(item["code"] for item in attempts if earned(item) or item["status"] == "prog")
    audit = audit_le_status(user.id)
    if audit:
        # APAS is authoritative: its covered categories count (AP and transfer credit included), and a
        # category the audit does not list is not required for this student.
        required, audited = audit
        covered |= audited | {category for item in items if item["kind"] == "le"
                              for category in item["categories"] if category not in required}
    # Materialize alternatives before generation so the engine callback is pure.
    suggestions = {}
    le_items = [item for item in items if item["kind"] == "le"]
    requests = set()
    for item in le_items:
        wanted = tuple(sorted(set(item["categories"]) - covered))
        for subset in {wanted, *((category,) for category in wanted)}:
            for season in {term.split()[0] for term in window}:
                requests.add((subset, season))
    for wanted, season in sorted(requests):
        key = (wanted, season)
        if key in suggestions:
            continue
        options, excluded = [], set(locked_codes(attempts))
        for _ in range(sum(len(slot["categories"]) for slot in le_items)):
            suggestion = suggest_le_course(wanted, season=season, exclude=excluded)
            if not suggestion:
                break
            code, coverage = suggestion
            record = resolve_course(code, program, find_courses([code]).get(code))
            excluded.add(code)
            if record:
                options.append((code, record, coverage))
        suggestions[key] = options

    def suggest(categories, term, exclude):
        wanted = set(categories)
        options = [option for (original, season), values in suggestions.items()
                   if wanted.intersection(original) and season == term.split()[0] for option in values
                   if option[0] not in exclude and wanted.intersection(option[2])]
        return min(options, key=lambda o: (-len(wanted.intersection(o[2])), o[0])) if options else None

    user_id, graduation, credit_load = user.id, user.graduation_target, user.credit_load
    existing = snapshot[4] if not program else {}
    db.session.rollback()
    earned_base = sum(max((float(row["credits"]) for row in attempts if row["code"] == code and earned(row)), default=0.0)
                      for code in {item["code"] for item in attempts})
    result = generate_plan(program, coursework=[item for item in attempts if item["status"] in {"done", "prog"}], metadata=metadata,
                    terms=window, credit_load=credit_load, base_credits=earned_base,
                    sample=sample, graduation=graduation, le_suggest=suggest, le_coverage=covered,
                    status="ok" if program else "unknown")
    planned = {item["code"]: (item["term"], "generated") for item in result["placements"]}
    if not program:
        # Unknown programs keep any user-added catalog courses; nothing is generated for them.
        planned = {code: value for code, value in existing.items() if value[1] == "user"}
    slots = {p["code"]: p["slot"] for p in result["placements"] if "slot" in p}
    plan = build_plan(user, context, planned, slots=slots)
    warnings = sorted(set(plan["warnings"]) | set(result["warnings"]))
    plan["warnings"] = warnings
    if not dry_run:
        lock_user(user_id)
        db.session.refresh(user)
        if generation_snapshot(user) != snapshot:
            raise PlanError(409, "plan_changed", "Your coursework, profile or plan changed during generation. Build again.")
        replace_planned_courses(user_id, planned, slots=slots, catalog_term=context.catalog_term, set_term=requested is not UNSET,
                                generated_at=datetime.now(timezone.utc))
        db.session.commit()
    return {"jobId": str(uuid4()), "status": "succeeded", "warnings": warnings, "plan": plan}
