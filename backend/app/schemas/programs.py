"""Strict validation of versioned academic seed data."""
import math
import re
from datetime import date
from urllib.parse import urlsplit

from app.schemas.coursework import CODE_PATTERN
from app.services.summary import GRADE_POINTS


class ProgramDataError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ProgramDataError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def number(value, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and (value > 0 if positive else value >= 0)
    except OverflowError:
        return False


def shape(value, required, optional=(), *, location="program"):
    require(isinstance(value, dict), f"{location} must be an object")
    require(not set(required) - value.keys(), f"{location} is missing required fields")
    require(not value.keys() - set(required) - set(optional), f"{location} contains unknown fields")


def validate_sources(sources):
    for key, source in sources.items():
        require(text(key), "Source keys must be nonempty text")
        shape(source, {"url", "retrieved", "section"}, location="source")
        require(text(source["section"]), "Source section must be nonempty text")
        require(text(source["url"]), "Source URL must be nonempty text")
        try:
            url = urlsplit(source["url"])
            require(url.scheme in {"http", "https"} and bool(url.hostname), "Source URL must use HTTP or HTTPS")
            retrieved = source["retrieved"]
            require(isinstance(retrieved, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved),
                    "Source retrieval date must use YYYY-MM-DD")
            date.fromisoformat(retrieved)
        except (TypeError, ValueError) as error:
            raise ProgramDataError("Invalid source URL or retrieval date") from error


def source_ref(value, sources):
    require(text(value) and value in sources, "Unknown source reference")


def grade_policy(policy, sources):
    shape(policy, {"minGrade", "allowS", "sourceRef"}, location="gradePolicy")
    minimum = policy["minGrade"]
    require(minimum is None or (isinstance(minimum, str) and minimum in GRADE_POINTS), "Invalid minimum grade")
    require(isinstance(policy["allowS"], bool), "allowS must be boolean")
    source_ref(policy["sourceRef"], sources)


def validate_groups(program):
    nodes = {}
    sources = program["sources"]

    def register(node):
        require(text(node["id"]), "Requirement IDs must be nonempty text")
        require(node["id"] not in nodes, "Requirement IDs must be globally unique")
        nodes[node["id"]] = node
        source_ref(node["sourceRef"], sources)
        if "label" in node:
            require(text(node["label"]), "Requirement labels must be nonempty text")
        if "gradePolicy" in node:
            grade_policy(node["gradePolicy"], sources)
        if "preferred" in node:
            require(isinstance(node["preferred"], bool), "preferred must be boolean")

    def rule(node):
        require(isinstance(node, dict), "Requirement rules must be objects")
        kind = node.get("type")
        required = {
            "course": {"code"}, "all": {"children", "allowReuse"}, "any": {"children"},
            "credits": {"courseSet", "minCredits"}, "count": {"courseSet"}, "review": {"message"},
        }
        require(isinstance(kind, str) and kind in required, "Unknown requirement node type")
        optional = {"label", "gradePolicy", "preferred"} | ({"minCourses", "maxCourses"} if kind == "count" else set())
        shape(node, {"id", "type", "sourceRef"} | required[kind], optional, location="requirement rule")
        register(node)
        if kind == "course":
            require(isinstance(node["code"], str) and CODE_PATTERN.fullmatch(node["code"]), "Invalid requirement course code")
        elif kind in {"all", "any"}:
            require(isinstance(node["children"], list) and bool(node["children"]), "Requirement children must be nonempty")
            if kind == "all":
                require(isinstance(node["allowReuse"], bool), "allowReuse must be boolean")
            for child in node["children"]:
                rule(child)
        elif kind in {"credits", "count"}:
            require(text(node["courseSet"]) and node["courseSet"] in program["courseSets"], "Unknown course set")
            if kind == "credits":
                require(number(node["minCredits"], positive=True), "minCredits must be finite and positive")
            else:
                require("minCourses" in node or "maxCourses" in node, "Count rules require a bound")
                for field in ("minCourses", "maxCourses"):
                    if field in node:
                        require(type(node[field]) is int and node[field] >= 0, "Count bounds must be nonnegative integers")
                if "minCourses" in node and "maxCourses" in node:
                    require(node["minCourses"] <= node["maxCourses"], "Count bounds are reversed")
        else:
            require(text(node["message"]), "Review rules require an explanation")

    for group in program["groups"]:
        shape(group, {"id", "label", "category", "sourceRef", "rule"}, {"gradePolicy"}, location="requirement group")
        register(group)
        require(isinstance(group["category"], str) and group["category"] in {"Major core", "Math and stats", "Elective", "Liberal ed"},
                "Unknown requirement category")
        rule(group["rule"])
    return nodes


def validate_allocation_declarations(program):
    for key, course_set in program["courseSets"].items():
        require(text(key), "Course set IDs must be nonempty text")
        shape(course_set, {"codes", "sourceRef"}, location="course set")
        source_ref(course_set["sourceRef"], program["sources"])
        codes = course_set["codes"]
        require(isinstance(codes, list) and bool(codes), "Course sets must be nonempty lists")
        require(all(isinstance(code, str) and CODE_PATTERN.fullmatch(code) for code in codes), "Invalid course set code")
        require(len(codes) == len(set(codes)), "Course set codes must be distinct")
    sharing = program.get("sharing", [])
    require(isinstance(sharing, list), "sharing must be a list")
    group_ids = {group["id"] for group in program["groups"]}
    declarations = set()
    for entry in sharing:
        shape(entry, {"groups", "sourceRef"}, location="sharing declaration")
        source_ref(entry["sourceRef"], program["sources"])
        groups = entry["groups"]
        require(isinstance(groups, list) and len(groups) >= 2, "Sharing requires at least two groups")
        require(all(text(group) and group in group_ids for group in groups), "Unknown sharing group")
        require(len(groups) == len(set(groups)), "Sharing groups must be distinct")
        key = tuple(sorted(groups))
        require(key not in declarations, "Duplicate sharing declaration")
        declarations.add(key)


def validate_adjustments(program, nodes):
    identities = set(nodes)
    affected = set()
    dependencies = {}
    for identity, node in nodes.items():
        dependencies[identity] = ([node["rule"]["id"]] if "rule" in node else
                                  [child["id"] for child in node.get("children", [])])
    for adjustment in program["adjustments"]:
        shape(adjustment, {"id", "sourceRef", "whenAnySatisfied", "effects"}, location="adjustment")
        identity = adjustment["id"]
        require(text(identity) and identity not in identities, "Adjustment IDs must be globally unique")
        identities.add(identity)
        source_ref(adjustment["sourceRef"], program["sources"])
        triggers = adjustment["whenAnySatisfied"]
        require(isinstance(triggers, list) and bool(triggers), "Adjustments require complete trigger branches")
        require(all(text(trigger) and trigger in nodes for trigger in triggers), "Unknown adjustment trigger")
        effects = adjustment["effects"]
        require(isinstance(effects, list) and bool(effects), "Adjustments require effects")
        for effect in effects:
            require(isinstance(effect, dict), "Adjustment effects must be objects")
            reducing = "reduceMinCredits" in effect
            shape(effect, {"targetId", "reduceMinCredits" if reducing else "satisfy"}, location="adjustment effect")
            target = effect["targetId"]
            require(text(target) and target in nodes, "Unknown adjustment target")
            require(target not in affected, "Multiple adjustments cannot affect the same target")
            affected.add(target)
            if reducing:
                reduction = effect["reduceMinCredits"]
                require(nodes[target].get("type") == "credits", "Credit reductions require a credits target")
                require(number(reduction, positive=True) and reduction <= nodes[target]["minCredits"], "Invalid credit reduction")
            else:
                require(effect["satisfy"] is True, "A waiver effect must explicitly satisfy the target")
            dependencies[target].extend(triggers)
    visited, visiting = set(), set()

    def visit(identity):
        require(identity not in visiting, "Adjustment dependency cycle")
        if identity in visited:
            return
        visiting.add(identity)
        for dependency in dependencies[identity]:
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    for identity in dependencies:
        visit(identity)


SEASONS = ("Fall", "Spring", "Summer")


def prerequisite_expression(node):
    require(isinstance(node, dict), "Prerequisite expressions must be objects")
    kind = node.get("type")
    if kind == "course":
        shape(node, {"type", "course_code"}, location="prerequisite course")
        require(isinstance(node["course_code"], str) and CODE_PATTERN.fullmatch(node["course_code"]),
                "Invalid prerequisite course code")
    elif kind in {"all_of", "any_of"}:
        shape(node, {"type", "requirements"}, location="prerequisite group")
        require(isinstance(node["requirements"], list) and bool(node["requirements"]), "Prerequisite groups must be nonempty")
        for child in node["requirements"]:
            prerequisite_expression(child)
    elif kind == "condition":
        shape(node, {"type", "text"}, location="prerequisite condition")
        require(text(node["text"]), "Prerequisite conditions require text")
    else:
        raise ProgramDataError("Unknown prerequisite expression type")


def validate_course_metadata(program):
    sources = program["sources"]
    for code, record in program["courseMetadata"].items():
        require(isinstance(code, str) and CODE_PATTERN.fullmatch(code), "Invalid supplemental course code")
        shape(record, {"catalogTerm", "title", "minimumCredits", "maximumCredits", "offered", "prerequisites", "sourceRef"},
              location="course metadata")
        require(record["catalogTerm"] == program["catalogTerm"], "Supplemental metadata must belong to the program catalog term")
        require(text(record["title"]), "Supplemental titles must be nonempty text")
        require(number(record["minimumCredits"]) and number(record["maximumCredits"]), "Supplemental credits must be finite")
        require(record["minimumCredits"] <= record["maximumCredits"], "Supplemental credit bounds are reversed")
        offered = record["offered"]
        require(offered is None or (isinstance(offered, list) and bool(offered) and len(offered) == len(set(offered))
                                    and all(season in SEASONS for season in offered)), "Invalid offered seasons")
        source_ref(record["sourceRef"], sources)
        prerequisites = record["prerequisites"]
        if prerequisites is not None:
            shape(prerequisites, {"expression", "sourceRef"}, location="prerequisite record")
            source_ref(prerequisites["sourceRef"], sources)
            if prerequisites["expression"] is not None:
                prerequisite_expression(prerequisites["expression"])


def validate_catalog_compatibility(program):
    mappings = program.get("catalogCompatibility", [])
    require(isinstance(mappings, list), "catalogCompatibility must be a list")
    seen = set()
    for mapping in mappings:
        shape(mapping, {"catalogVersion", "catalogTerm", "sourceRef"}, location="catalog compatibility")
        version = mapping["catalogVersion"]
        require(text(version) and version.strip().lower() != "unknown", "Catalog compatibility needs a verified catalog version")
        require(mapping["catalogTerm"] == program["catalogTerm"], "Catalog compatibility must map to the program catalog term")
        source_ref(mapping["sourceRef"], program["sources"])
        require(version not in seen, "Duplicate catalog compatibility mapping")
        seen.add(version)


def validate_program(program):
    shape(program, {
        "schemaVersion", "id", "name", "officialProgramId", "catalogTerm", "totalCredits",
        "source", "sources", "courseSets", "courseMetadata", "groups", "adjustments",
    }, {"officialName", "sharing", "catalogCompatibility", "preferredCourses"})
    if "preferredCourses" in program:
        require(isinstance(program["preferredCourses"], list) and all(isinstance(code, str) and CODE_PATTERN.fullmatch(code) for code in program["preferredCourses"]), "preferredCourses must list course codes")
    require(type(program["schemaVersion"]) is int and program["schemaVersion"] == 2, "Unsupported program schema version")
    for field in ("id", "name", "officialProgramId", "source"):
        require(text(program[field]), f"{field} must be nonempty text")
    if "officialName" in program:
        require(text(program["officialName"]), "officialName must be nonempty text")
    require(isinstance(program["catalogTerm"], str) and re.fullmatch(r"(Fall|Spring|Summer) [1-9]\d{3}", program["catalogTerm"]),
            "catalogTerm must identify a valid catalog season and year")
    require(number(program["totalCredits"], positive=True), "totalCredits must be finite and positive")
    for field in ("sources", "courseSets", "courseMetadata"):
        require(isinstance(program[field], dict), f"{field} must be an object")
    require(bool(program["sources"]), "sources must not be empty")
    validate_sources(program["sources"])
    require(isinstance(program["groups"], list) and bool(program["groups"]), "groups must be a nonempty list")
    require(isinstance(program["adjustments"], list), "adjustments must be a list")
    nodes = validate_groups(program)
    validate_allocation_declarations(program)
    validate_adjustments(program, nodes)
    validate_course_metadata(program)
    validate_catalog_compatibility(program)
    return program
