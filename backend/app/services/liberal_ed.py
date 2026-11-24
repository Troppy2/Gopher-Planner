"""Liberal education tracker for UMN Twin Cities: diversified core, designated themes, writing.

The rules live in ``data/liberal_ed/umn-tc.json`` with their official sources. Course evidence
comes from catalog designations; a parsed APAS audit takes precedence where it says something.
A course can count once per kind (one core, one theme, writing intensive), so the same course
can satisfy a core and a theme at once, and no course ever has to be allocated between two cores.
"""
import json
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[2] / "data" / "liberal_ed" / "umn-tc.json"
KINDS = ("done", "prog", "plan")
ITEM_STATUS = {"done": "done", "prog": "in_progress", "plan": "planned"}


@lru_cache(maxsize=1)
def load_rules():
    with RULES_PATH.open(encoding="utf-8") as handle:
        rules = json.load(handle)
    if rules.get("schemaVersion") != 1:
        raise ValueError("Unsupported liberal education rules version")
    return rules


def _codes_by_kind(courses, matches):
    found = {kind: [] for kind in KINDS}
    for course in courses:
        if course["status"] in found and matches(course["code"]) and course["code"] not in found[course["status"]]:
            found[course["status"]].append(course["code"])
    return {kind: sorted(codes) for kind, codes in found.items()}


def _course_status(codes):
    return next((ITEM_STATUS[kind] for kind in KINDS if codes[kind]), "needed")


def _category_items(section, courses, designations, audit):
    """Evaluate each core or theme category. APAS rules apply only if the audit lists this section."""
    required, covered = audit or (set(), set())
    names = {name for entry in section["items"] for name in entry["designations"]}
    audit_applies = bool(required & names)
    items = []
    for entry in section["items"]:
        wanted = set(entry["designations"])
        codes = _codes_by_kind(courses, lambda code: bool(designations.get(code, set()) & wanted))
        status, source = _course_status(codes), "catalog"
        if audit_applies:
            if wanted & covered:
                status, source = "done", "apas"
            elif not wanted & required:
                status = "not_required"
            elif status == "done":
                # The catalog says it is complete, but the audit does not show it yet.
                status = "needs_review"
        items.append({"id": entry["id"], "label": entry["label"], "designations": entry["designations"],
                      "status": status, "source": source, "codes": codes})
    return items


def _section_status(items, *, met, on_track):
    if met:
        return "met"
    if any(entry["status"] == "needs_review" for entry in items):
        return "needs_review"
    return "on_track" if on_track else "short"


def _number(code):
    digits = "".join(ch for ch in code.split(" ")[-1] if ch.isdigit())
    return int(digits) if digits else 0


def evaluate_liberal_ed(rules, *, courses, designations, major_codes, major_subjects, audit=None):
    """Tracker state for one student.

    ``courses``: ``{"code", "status", "term"}`` with status ``done`` (earned), ``prog`` or ``plan``.
    ``designations``: course code to its set of catalog designation names.
    ``major_codes`` / ``major_subjects``: what counts as "in the major" for writing intensive.
    ``audit``: ``(required, covered)`` designation names from a parsed APAS audit, or None.
    """
    complete = {"done", "not_required"}
    projected_ok = complete | {"in_progress", "planned"}

    core_items = _category_items(rules["core"], courses, designations, audit)
    core = {"status": _section_status(core_items,
                                      met=all(entry["status"] in complete for entry in core_items),
                                      on_track=all(entry["status"] in projected_ok for entry in core_items)),
            "items": core_items}

    theme_rules = rules["themes"]
    theme_items = _category_items(theme_rules, courses, designations, audit)
    by_id = {entry["id"]: entry for entry in theme_items}
    completed = sum(entry["status"] == "done" for entry in theme_items)
    projected = sum(entry["status"] in {"done", "in_progress", "planned"} for entry in theme_items)
    mandatory_missing = [identity for identity in theme_rules["mandatory"] if by_id[identity]["status"] not in complete]
    mandatory_unplanned = [identity for identity in theme_rules["mandatory"] if by_id[identity]["status"] not in projected_ok]
    themes = {"status": _section_status(theme_items,
                                        met=completed >= theme_rules["required"] and not mandatory_missing,
                                        on_track=projected >= theme_rules["required"] and not mandatory_unplanned),
              "required": theme_rules["required"], "completed": completed, "projected": projected,
              "mandatory": list(theme_rules["mandatory"]), "mandatoryMissing": mandatory_missing, "items": theme_items}

    writing_rules = rules["writing"]
    first_codes = _codes_by_kind(courses, lambda code: code in writing_rules["firstYear"]["codes"])
    first_year = {"label": writing_rules["firstYear"]["label"], "status": _course_status(first_codes),
                  "codes": first_codes, "acceptedCodes": list(writing_rules["firstYear"]["codes"])}

    intensive_rules = writing_rules["intensive"]
    wi_names = set(intensive_rules["designations"])
    wi_codes = _codes_by_kind(courses, lambda code: bool(designations.get(code, set()) & wi_names))

    def tally(kinds):
        codes = sorted({code for kind in kinds for code in wi_codes[kind]})
        upper = [code for code in codes if _number(code) >= 3000]
        in_major = [code for code in upper if code in major_codes or code.split(" ")[0] in major_subjects]
        return {"total": len(codes), "upper": len(upper), "upperInMajor": len(in_major)}

    def enough(counts):
        return (counts["total"] >= intensive_rules["total"] and counts["upper"] >= intensive_rules["upperDivision"]
                and counts["upperInMajor"] >= intensive_rules["upperDivisionInMajor"])

    wi_done, wi_projected = tally(["done"]), tally(KINDS)
    intensive = {"label": intensive_rules["label"],
                 "status": "met" if enough(wi_done) else "on_track" if enough(wi_projected) else "short",
                 "required": {"total": intensive_rules["total"], "upper": intensive_rules["upperDivision"],
                              "upperInMajor": intensive_rules["upperDivisionInMajor"]},
                 "completed": wi_done, "projected": wi_projected, "codes": wi_codes}

    # Designations a new course could still usefully cover, for "double dipper" suggestions.
    remaining = [entry["designations"][0] for entry in core_items if entry["status"] == "needed"]
    if projected < theme_rules["required"] or mandatory_unplanned:
        remaining += [entry["designations"][0] for entry in theme_items if entry["status"] == "needed"]
    if intensive["status"] == "short":
        remaining += sorted(wi_names)

    return {"source": "catalog+apas" if audit else "catalog", "core": core, "themes": themes,
            "writing": {"firstYear": first_year, "intensive": intensive}, "remaining": remaining,
            "sources": {key: value["url"] for key, value in rules["sources"].items()}}


def open_needs(rules, covered, wi_count):
    """Liberal education needs a plan should still fill, most constrained first.

    ``covered`` is every designation name already earned, in progress, planned, or credited by APAS;
    ``wi_count`` counts writing intensive courses among them. Returns ``[(label, designations)]``:
    mandatory themes, then missing core areas, then other themes while fewer than the required
    number are covered, then writing intensive while the total is short. Upper-division and
    in-major writing intensive courses depend on the major and are left to the tracker.
    """
    def met(entry):
        return bool(covered & set(entry["designations"]))

    themes = rules["themes"]
    by_id = {entry["id"]: entry for entry in themes["items"]}
    needs = [(by_id[identity]["designations"][0], set(by_id[identity]["designations"]))
             for identity in themes["mandatory"] if not met(by_id[identity])]
    needs += [(entry["designations"][0], set(entry["designations"])) for entry in rules["core"]["items"] if not met(entry)]
    if sum(met(entry) for entry in themes["items"]) < themes["required"]:
        needs += [(entry["designations"][0], set(entry["designations"])) for entry in themes["items"]
                  if not met(entry) and entry["id"] not in themes["mandatory"]]
    intensive = rules["writing"]["intensive"]
    if wi_count < intensive["total"]:
        needs.append((intensive["designations"][0], set(intensive["designations"])))
    return needs


def designation_groups(rules=None):
    """Each designation name mapped to every name that satisfies the same category (former names included)."""
    rules = rules or load_rules()
    groups = {}
    for section in ("core", "themes"):
        for entry in rules[section]["items"]:
            for name in entry["designations"]:
                groups[name] = list(entry["designations"])
    for name in rules["writing"]["intensive"]["designations"]:
        groups[name] = [name]
    return groups


def designation_label_categories(label):
    """Designation names in a generated slot label such as "Race, Power, and Justice US, Literature".

    Names can contain commas, so known names are matched longest first instead of splitting. Returns
    the names in label order, or [] when anything else is left over (an unknown or made-up label)."""
    if not isinstance(label, str) or not label.strip():
        return []
    rest, found = label, []
    for name in sorted(designation_groups(), key=len, reverse=True):
        if name in rest:
            found.append((label.index(name), name))
            rest = rest.replace(name, "")
    if not found or rest.replace(",", "").strip():
        return []
    return [name for _, name in sorted(found)]
