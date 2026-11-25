"""Map official UMN catalog program snapshots to versioned v2 planner files.

Mapping is deliberately conservative. Structures the v2 contract can express exactly are
mapped; anything else (free text, attribute-defined lists, unresolved courses, ambiguous
nested lists) becomes an explicit ``review`` rule so it is never silently satisfied.
Program-specific rules stated only in prose are added through sourced overlay files.
"""
import argparse
import copy
import csv
import html
import itertools
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.schemas.coursework import CODE_PATTERN  # noqa: E402
from app.schemas.programs import validate_program  # noqa: E402
from app.services.requisites import load_enforced, load_reviewed, resolve_prerequisites  # noqa: E402

COURSE_LIST_CONDITIONS = {"minimumCredits", "completeVariableCoursesAndVariableCredits", "completedAllOf",
                          "completedAnyOf", "completedAtLeastXOf"}
MAX_COMBINATIONS = 20
REVIEW_SUFFIX = "Verify this requirement with your advisor or APAS."


class ProgramSkipped(ValueError):
    pass


def plain(text):
    text = re.sub(r"<br\s*/?>|</p>", "\n", text or "", flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\s*\n\s*", "\n", text)).strip()


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.replace(".", "").lower()).strip("-")


def catalog_term(date):
    year, month = int(date[:4]), int(date[5:7])
    return f"{'Spring' if month <= 5 else 'Summer' if month <= 7 else 'Fall'} {year}"


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return int(result) if result.is_integer() else result


def positive(value):
    result = number(value)
    return result if result and result > 0 else None


# Prerequisite text: only expressions made entirely of course codes and unambiguous connectors become trees.
TOKEN = re.compile(r"\s*(?:(?P<course>(?!(?:or|and)\s)[A-Za-z]{2,6}\s+\d{4}[A-Za-z]?\b)|(?P<number>\d{4}[A-Za-z]?\b)|"
                   r"(?P<word>\bor\b|\band\b)|(?P<punct>[,;()\[\]]))", re.IGNORECASE)


class Ambiguous(ValueError):
    pass


def _tokens(text):
    position, tokens, subject = 0, [], None
    stripped = text.strip().rstrip(".")
    while position < len(stripped):
        match = TOKEN.match(stripped, position)
        if not match or match.end() == position:
            raise Ambiguous(text)
        position = match.end()
        if match.group("course"):
            subject, digits = match.group("course").split()
            tokens.append(("code", f"{subject.upper()} {digits.upper()}"))
        elif match.group("number"):
            if subject is None:
                raise Ambiguous(text)
            tokens.append(("code", f"{subject.upper()} {match.group('number').upper()}"))
        elif match.group("word"):
            tokens.append(("or" if match.group("word").lower() == "or" else "and", None))
        else:
            punct = match.group("punct")
            tokens.append((punct if punct in "()[]" else "and", None))
    return tokens


def _parse(tokens, index, closing):
    items, connectors = [], set()
    while index < len(tokens):
        kind, value = tokens[index]
        if kind in ")]":
            if closing != kind:
                raise Ambiguous("unbalanced")
            break
        if kind in "([":
            node, index = _parse(tokens, index + 1, ")" if kind == "(" else "]")
            items.append(node)
        elif kind == "code":
            items.append({"type": "course", "course_code": value})
        else:
            if not items:
                raise Ambiguous("leading connector")
            connectors.add(kind)
        index += 1
    else:
        if closing:
            raise Ambiguous("unbalanced")
    if not items or len(connectors) > 1 or (len(items) > 1 and not connectors):
        raise Ambiguous("mixed")
    if len(items) == 1:
        return items[0], index
    return {"type": "any_of" if connectors == {"or"} else "all_of", "requirements": items}, index


def parse_prerequisites(text):
    """A course-code tree, a sourced free-text condition, or None for an explicit statement of no prerequisites."""
    if text.strip().rstrip(".").lower() in {"none", "no prerequisites"}:
        return None
    try:
        node, _ = _parse(_tokens(text), 0, None)
        return node
    except Ambiguous:
        return {"type": "condition", "text": text}


def offered(text):
    text = (text or "").strip()
    if not text.startswith("Every"):
        return None
    seasons = [season for season in ("Fall", "Spring", "Summer") if season in text]
    return seasons or None


class Builder:
    def __init__(self, record, courses, *, enforced=None, reviewed=None, reviewed_sources=None):
        self.record = record
        self.courses = courses
        self.enforced = enforced or {}
        self.reviewed = reviewed or {}
        self.reviewed_sources = reviewed_sources or {}
        self.known = {" ".join(row["code"].split()) for row in courses.values() if row["code"].strip()}
        self.subjects = {code.split()[0] for code in self.known}
        self.term = catalog_term(record["effective_start_date"])
        self.ids = set()
        self.sets = {}
        self.metadata = {}
        self.sources = {"program": {
            "url": record["source_url"], "retrieved": record["retrieved_at_utc"][:10],
            "section": f"Official program requirements, revision {record['revision_id']}"}}

    def uid(self, base):
        identity, counter = base, 2
        while identity in self.ids:
            identity, counter = f"{base}-{counter}", counter + 1
        self.ids.add(identity)
        return identity

    def course_code(self, gid):
        row = self.courses.get(gid)
        if not row or not row["title"] or number(row["credits_min"]) is None or number(row["credits_max"]) is None:
            return None
        if not CODE_PATTERN.fullmatch(row["code"]):
            return None
        if row["code"] not in self.metadata:
            self.add_metadata(row)
        return row["code"]

    def add_metadata(self, row):
        key = f"course-{row['course_group_id']}"
        self.sources[key] = {"url": row["source_url"], "retrieved": row["retrieved_at_utc"][:10],
                             "section": f"Course record {row['code']}, version {row['revision_id']}"}
        code = row["code"]
        expression, origin, _ = resolve_prerequisites(
            code, row["prerequisite_text"], enforced=self.enforced, reviewed=self.reviewed,
            subject=code.split()[0], subjects=self.subjects, known=self.known)
        prerequisite_source = key
        if origin == "enforced":
            entry = self.enforced[code]
            prerequisite_source = f"enforced-{code.replace(' ', '-')}"
            self.sources[prerequisite_source] = {
                "url": entry["url"], "retrieved": entry["retrieved"],
                "section": f"Enrollment requirement enforced by registration for {code}, term {entry['strm']}"}
        elif origin == "reviewed":
            prerequisite_source = self.reviewed[code]["sourceRef"]
            self.sources[prerequisite_source] = self.reviewed_sources[prerequisite_source]
        self.metadata[code] = {
            "catalogTerm": self.term, "title": row["title"], "minimumCredits": number(row["credits_min"]),
            "maximumCredits": number(row["credits_max"]), "offered": offered(row["typically_offered"]),
            "prerequisites": {"expression": expression, "sourceRef": prerequisite_source},
            "sourceRef": key,
        }

    def review(self, base, message, label=None):
        node = {"id": self.uid(base), "type": "review", "sourceRef": "program",
                "message": f"{message.strip()} {REVIEW_SUFFIX}".strip()}
        if label:
            node["label"] = label
        return node

    def course(self, code, base):
        return {"id": self.uid(base), "type": "course", "code": code, "sourceRef": "program"}

    def labelled(self, node, rule):
        name = plain(rule.get("name") or "")
        if name:
            node["label"] = name
        return node

    def rule(self, rule):
        condition = rule.get("condition")
        identity = f"r-{rule.get('id')}"
        name = plain(rule.get("name") or "") or "This requirement"
        subs = rule.get("subRules") or []
        has_courses = isinstance(rule.get("value"), dict) and rule["value"].get("condition") == "courses"
        if condition == "none":
            return None
        if condition == "freeformText":
            return self.review(identity, plain(rule.get("value") if isinstance(rule.get("value"), str) else name), name)
        if condition in {"allOf", "anyOf", "numberOf"} or (subs and condition in COURSE_LIST_CONDITIONS and not has_courses):
            return self.composite(rule, identity, name)
        if condition in COURSE_LIST_CONDITIONS:
            if subs:
                return self.review(identity, f"{name} combines nested rules with a course list.", name)
            if not has_courses:
                return self.review(identity, f"{name} uses a course list the planner cannot read.", name)
            return self.labelled(self.course_list(rule, identity, name), rule)
        return self.review(identity, f"{name} uses an unsupported rule type.", name)

    def composite(self, rule, identity, name):
        condition = rule.get("condition")
        outer = self.uid(identity)
        children = [node for node in (self.rule(sub) for sub in rule.get("subRules") or []) if node is not None]
        if not children:
            self.ids.discard(outer)
            return None
        if condition == "anyOf":
            return self.labelled({"id": outer, "type": "any", "sourceRef": "program", "children": children}, rule)
        if condition == "numberOf":
            count = int(number(rule.get("number")) or 0)
            if count <= 0:
                self.ids.discard(outer)
                return self.review(identity, f"{name} has no machine-checkable count.", name)
            if count < len(children):
                combinations = list(itertools.combinations(range(len(children)), count))
                if len(combinations) > MAX_COMBINATIONS:
                    self.ids.discard(outer)
                    return self.review(identity, f"{name} offers too many combinations to list.", name)
                branches = []
                for index, chosen in enumerate(combinations, 1):
                    parts = [self.renamed(children[position], f"c{index}") for position in chosen]
                    branches.append({"id": self.uid(f"{outer}-c{index}"), "type": "all", "allowReuse": False,
                                     "sourceRef": "program", "children": parts})
                for child in children:
                    self.forget(child)
                return self.labelled({"id": outer, "type": "any", "sourceRef": "program", "children": branches}, rule)
        node = {"id": outer, "type": "all", "allowReuse": False, "sourceRef": "program", "children": children}
        minimum = positive(rule.get("minCredits")) or positive(rule.get("credits"))
        codes = self.subtree_codes(node)
        if minimum and codes:
            node["id"] = self.uid(f"{outer}-rules")
            set_id = self.add_set(f"set-{rule.get('id')}", codes)
            total = {"id": self.uid(f"{outer}-credits"), "type": "credits", "courseSet": set_id,
                     "minCredits": minimum, "sourceRef": "program"}
            node = {"id": outer, "type": "all", "allowReuse": True, "sourceRef": "program", "children": [node, total]}
        return self.labelled(node, rule)

    def forget(self, node):
        self.ids.discard(node["id"])
        for child in node.get("children", []):
            self.forget(child)

    def renamed(self, node, suffix):
        node = copy.deepcopy(node)

        def walk(item):
            item["id"] = self.uid(f"{item['id']}-{suffix}")
            for child in item.get("children", []):
                walk(child)

        walk(node)
        return node

    def subtree_codes(self, node):
        codes = []
        if node["type"] == "course":
            codes.append(node["code"])
        if node["type"] in {"credits", "count"}:
            codes.extend(self.sets[node["courseSet"]]["codes"])
        for child in node.get("children", []):
            codes.extend(code for code in self.subtree_codes(child) if code not in codes)
        return list(dict.fromkeys(codes))

    def add_set(self, base, codes):
        identity, counter = base, 2
        while identity in self.sets:
            identity, counter = f"{base}-{counter}", counter + 1
        self.sets[identity] = {"codes": list(dict.fromkeys(codes)), "sourceRef": "program"}
        return identity

    def unresolved_review(self, identity):
        return self.review(f"{identity}-unresolved", "Some listed course options could not be resolved to current official course records.")

    def course_list(self, rule, identity, name):
        groups = [(group.get("logic") or "and", [self.course_code(gid) for gid in group.get("value") or []])
                  for group in rule["value"].get("values") or [] if group.get("value")]
        flat = list(dict.fromkeys(code for _, codes in groups for code in codes if code))
        unresolved = any(code is None for _, codes in groups for code in codes)
        min_courses = number(rule.get("minCourses"))
        if rule.get("condition") == "completedAtLeastXOf" and not min_courses:
            min_courses = number(rule.get("number"))
        min_courses = min_courses if min_courses and min_courses > 0 else None
        max_courses = number(rule.get("maxCourses"))
        max_courses = max_courses if max_courses is not None and max_courses > 0 else None
        min_credits = positive(rule.get("minCredits")) or positive(rule.get("credits"))
        max_credits = positive(rule.get("maxCredits"))
        no_bounds = min_courses is None and max_courses is None and min_credits is None
        all_and = all(logic == "and" for logic, _ in groups)
        if not groups:
            return self.review(identity, f"{name} lists no courses.", name)
        if no_bounds and max_credits:
            # v2 has no credit cap; a cap-only list is not a list of required courses.
            return self.review(identity, f"{name}: courses from this list count for at most {max_credits:g} credits.", name)
        if rule.get("condition") == "completedAllOf" or (no_bounds and all_and):
            if unresolved or not flat:
                return self.review(identity, f"{name} requires courses that could not be resolved.", name)
            if len(flat) == 1:
                return self.course(flat[0], identity)
            return {"id": self.uid(identity), "type": "all", "allowReuse": False, "sourceRef": "program",
                    "children": [self.course(code, f"{identity}-{index}") for index, code in enumerate(flat, 1)]}
        if not flat:
            return self.review(identity, f"{name} lists courses that could not be resolved.", name)
        minimum = number(self.metadata[flat[0]]["minimumCredits"]) if len(flat) == 1 else None
        if (len(flat) == 1 and not unresolved and (min_courses or 1) <= 1
                and (min_credits is None or (minimum is not None and min_credits <= minimum))):
            return self.course(flat[0], identity)
        single_groups = all(logic == "or" or len(codes) == 1 for logic, codes in groups)
        if len(groups) > 1 and min_courses == len(groups) and single_groups:
            outer = self.uid(identity)
            parts = []
            for index, (_, codes) in enumerate(groups, 1):
                known = [code for code in codes if code]
                if not known:
                    self.ids.discard(outer)
                    return self.review(identity, f"{name} requires courses that could not be resolved.", name)
                options = [self.course(code, f"{identity}-g{index}-{position}") for position, code in enumerate(known, 1)]
                if len(known) < len(codes):
                    options.append(self.unresolved_review(f"{identity}-g{index}"))
                parts.append(options[0] if len(options) == 1 else
                             {"id": self.uid(f"{identity}-g{index}"), "type": "any", "sourceRef": "program", "children": options})
            sequence = {"id": outer, "type": "all", "allowReuse": False, "sourceRef": "program", "children": parts}
            if not min_credits:
                return sequence
            sequence["id"] = self.uid(f"{identity}-sequence")
            total = {"id": self.uid(f"{identity}-credits"), "type": "credits", "minCredits": min_credits,
                     "courseSet": self.add_set(f"set-{rule.get('id')}", flat), "sourceRef": "program"}
            return {"id": outer, "type": "all", "allowReuse": True, "sourceRef": "program", "children": [sequence, total]}
        if min_courses == 1 and max_courses in (None, 1) and min_credits is None and single_groups:
            options = [self.course(code, f"{identity}-{index}") for index, code in enumerate(flat, 1)]
            if unresolved:
                options.append(self.unresolved_review(identity))
            if len(options) == 1:
                options[0]["id"] = self.uid(identity)
                return options[0]
            return {"id": self.uid(identity), "type": "any", "sourceRef": "program", "children": options}
        if no_bounds:
            return self.review(identity, f"{name} states no machine-checkable course or credit bound.", name)
        set_id = self.add_set(f"set-{rule.get('id')}", flat)
        outer = self.uid(identity)
        children = []
        if min_credits:
            children.append({"id": self.uid(f"{identity}-credits"), "type": "credits", "courseSet": set_id,
                             "minCredits": min_credits, "sourceRef": "program"})
        if min_courses:
            children.append({"id": self.uid(f"{identity}-min"), "type": "count", "courseSet": set_id,
                             "minCourses": int(min_courses), "sourceRef": "program"})
        if max_courses:
            children.append({"id": self.uid(f"{identity}-max"), "type": "count", "courseSet": set_id,
                             "maxCourses": int(max_courses), "sourceRef": "program"})
        if len(children) == 1:
            self.ids.discard(outer)
            self.ids.discard(children[0]["id"])
            children[0]["id"] = self.uid(identity)
            pool = children[0]
        else:
            pool = {"id": outer, "type": "all", "allowReuse": True, "sourceRef": "program", "children": children}
        if not unresolved:
            return pool
        pool = self.renamed(pool, "listed")
        self.forget_ids(identity)
        return {"id": self.uid(identity), "type": "any", "sourceRef": "program",
                "children": [pool, self.unresolved_review(identity)]}

    def forget_ids(self, identity):
        self.ids.discard(identity)


def category(name):
    lowered = name.lower()
    if any(word in lowered for word in ("math", "statistic", "calculus")):
        return "Math and stats"
    if "elective" in lowered:
        return "Elective"
    if "liberal" in lowered:
        return "Liberal ed"
    return "Major core"


def referenced(program):
    codes = set()

    def walk(node):
        if node["type"] == "course":
            codes.add(node["code"])
        if node["type"] in {"credits", "count"}:
            codes.update(program["courseSets"][node["courseSet"]]["codes"])
        for child in node.get("children", []):
            walk(child)

    for group in program["groups"]:
        walk(group["rule"])
    return codes


def build_program(record, courses, *, overlay=None, enforced=None, reviewed=None, reviewed_sources=None):
    total = positive(record.get("degree_credits_min"))
    if not total:
        raise ProgramSkipped("The official record states no degree credit total")
    builder = Builder(record, courses, enforced=enforced, reviewed=reviewed, reviewed_sources=reviewed_sources)
    groups, sub_plans = [], []
    for section in (record["requirements"] or {}).get("requisitesSimple") or []:
        name = plain(section.get("name") or "") or "Program requirements"
        if section.get("requirementLevel") == "programSubPlanRequirements":
            if section.get("rules") or section.get("notes"):
                sub_plans.append(name)
            continue
        rules = [node for node in (builder.rule(rule) for rule in section.get("rules") or []) if node is not None]
        if not rules:
            if plain(section.get("notes") or ""):
                rules = [builder.review(f"r-{section.get('id')}", plain(section["notes"]), name)]
            else:
                continue
        rule = rules[0] if len(rules) == 1 else {"id": builder.uid(f"r-{section.get('id')}"), "type": "all",
                                                   "allowReuse": False, "sourceRef": "program", "children": rules}
        groups.append({"id": builder.uid(f"g-{section.get('id')}"), "label": name, "category": category(name),
                       "sourceRef": "program", "rule": rule})
    level_labels = {"programRequirements": "Additional program requirements",
                    "programAdmissionRequirements": "Program admission requirements"}
    for level in record.get("requirement_levels") or []:
        text = plain(level.get("notes") or "")
        if text and level.get("key") in level_labels:
            groups.append({"id": builder.uid(f"g-notes-{level['key']}"), "label": level_labels[level["key"]],
                           "category": "Liberal ed" if "liberal education" in text.lower() else "Major core",
                           "sourceRef": "program", "rule": builder.review(f"r-notes-{level['key']}", text)})
    if sub_plans:
        groups.append({"id": builder.uid("g-sub-plans"), "label": "Sub-plan requirements", "category": "Major core",
                       "sourceRef": "program", "rule": builder.review(
                           "r-sub-plans", f"Complete any sub-plan requirements that apply to you: {', '.join(sub_plans)}.")})
    if not groups:
        raise ProgramSkipped("The official record lists no requirement sections")
    name = record["name"]
    program = {
        "schemaVersion": 2, "id": slug(name), "name": name, "officialName": name,
        "officialProgramId": record["program_id"], "catalogTerm": builder.term, "totalCredits": total,
        "source": (f"{name}, revision {record['revision_id']}, {record['source_url']}, retrieved "
                   f"{record['retrieved_at_utc'][:10]}. Machine-mapped from the official catalog; review rules mark "
                   "obligations that could not be verified automatically."),
        "sources": builder.sources, "courseSets": builder.sets, "courseMetadata": builder.metadata,
        "groups": groups, "sharing": [], "adjustments": [],
    }
    if overlay:
        apply_overlay(program, overlay, builder)
    used_sets = set()

    def sets_in(node):
        if node["type"] in {"credits", "count"}:
            used_sets.add(node["courseSet"])
        for child in node.get("children", []):
            sets_in(child)

    for group in program["groups"]:
        sets_in(group["rule"])
    program["courseSets"] = {key: value for key, value in program["courseSets"].items() if key in used_sets}
    used = referenced(program)
    program["courseMetadata"] ={code: value for code, value in sorted(program["courseMetadata"].items()) if code in used}
    keep = ({"program"} | {value["sourceRef"] for value in program["courseMetadata"].values()}
            | {value["prerequisites"]["sourceRef"] for value in program["courseMetadata"].values() if value["prerequisites"]}
            | set(overlay.get("sources", {}) if overlay else ()))
    program["sources"] = {key: value for key, value in program["sources"].items() if key in keep}
    return program


def apply_overlay(program, overlay, builder):
    by_code = {row["code"]: row for row in builder.courses.values()}
    for key in ("id", "name", "officialName"):
        if key in overlay:
            program[key] = overlay[key]
    program["sources"].update(overlay.get("sources", {}))
    if overlay.get("sourceNote"):
        program["source"] += " " + overlay["sourceNote"]
    program["groups"] = [group for group in program["groups"] if group["id"] not in set(overlay.get("dropGroups", []))]
    replacements = overlay.get("replaceRules", {})

    def replace(node):
        if node["id"] in replacements:
            return copy.deepcopy(replacements[node["id"]])
        if "children" in node:
            node["children"] = [replace(child) for child in node["children"]]
        return node

    for group in program["groups"]:
        group["rule"] = replace(group["rule"])
    preferred = set(overlay.get("preferredRules", []))

    def prefer(node):
        if node["id"] in preferred:
            node["preferred"] = True
        for child in node.get("children", []):
            prefer(child)

    for group in program["groups"]:
        prefer(group["rule"])
    program["groups"].extend(copy.deepcopy(overlay.get("addGroups", [])))
    program["courseSets"].update(copy.deepcopy(overlay.get("courseSets", {})))
    program["sharing"] = copy.deepcopy(overlay.get("sharing", []))
    if overlay.get("preferredCourses"):
        program["preferredCourses"] = list(overlay["preferredCourses"])
    program["adjustments"] = copy.deepcopy(overlay.get("adjustments", []))
    if overlay.get("gradePolicy"):
        for group in program["groups"]:
            if group["id"] not in set(overlay.get("ungradedGroups", [])):
                group.setdefault("gradePolicy", copy.deepcopy(overlay["gradePolicy"]))
    for code in sorted(referenced(program) - set(program["courseMetadata"])):
        if code not in by_code:
            raise ProgramSkipped(f"Overlay references {code}, which has no official course record")
        builder.add_metadata(by_code[code])
        program["courseMetadata"][code] = builder.metadata[code]
    program["sources"].update(builder.sources)


def read_csv(path):
    csv.field_size_limit(100_000_000)
    with open(path, encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--programs", type=Path, required=True)
    parser.add_argument("--courses", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overlays", type=Path, default=Path(__file__).parent / "program_overlays")
    parser.add_argument("--requisites", type=Path, help="Enforced enrollment requirements from export_requisites.py")
    parser.add_argument("--reviewed", type=Path, default=BACKEND / "data" / "prerequisites" / "reviewed.json",
                        help="Hand-reviewed prerequisite trees, which take precedence over parsed text")
    parser.add_argument("--replace", action="store_true", help="Replace previously generated files in the output directory")
    args = parser.parse_args(argv)
    courses = {row["course_group_id"]: row for row in read_csv(args.courses)}
    enforced = load_enforced(args.requisites)
    reviewed, reviewed_sources = load_reviewed(args.reviewed if args.reviewed and args.reviewed.exists() else None)
    overlays = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(args.overlays.glob("*.json"))}
    args.output.mkdir(parents=True, exist_ok=True)
    report, written = [], 0
    for row in read_csv(args.programs):
        if row["career"] != "Undergraduate" or row["program_type"] != "Major":
            continue
        record = {**row, "requirements": json.loads(row["requirements_json"]),
                  "requirement_levels": json.loads(row["requirement_levels_json"])}
        try:
            program = validate_program(build_program(record, courses, overlay=overlays.get(row["program_id"]),
                                                     enforced=enforced, reviewed=reviewed, reviewed_sources=reviewed_sources))
        except ProgramSkipped as error:
            report.append({"program_id": row["program_id"], "name": row["name"], "file": "", "catalog_term": "",
                           "review_rules": "", "status": f"skipped: {error}"})
            continue
        path = args.output / f"{program['id']}--{program['catalogTerm'].lower().replace(' ', '-')}.json"
        if path.exists() and not args.replace:
            raise FileExistsError(f"{path} exists; pass --replace to regenerate")
        path.write_text(json.dumps(program, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
        written += 1
        reviews = json.dumps(program["groups"]).count('"type": "review"')
        report.append({"program_id": row["program_id"], "name": program["name"], "file": path.name,
                       "catalog_term": program["catalogTerm"], "review_rules": reviews,
                       "status": "overlay" if row["program_id"] in overlays else "mapped"})
    with (args.output / "mapping-report.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["program_id", "name", "file", "catalog_term", "review_rules", "status"])
        writer.writeheader()
        writer.writerows(report)
    print(f"Wrote {written} undergraduate major files; {len(report) - written} skipped. See mapping-report.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
