"""Course nodes and prerequisite edges for one program version, for the flow-chart graph.

Nodes are every course the program references. Edges come from the same resolved
prerequisite metadata the planner uses, so the graph and plan validation agree.
"""
from app.repositories.catalog import find_courses
from app.services.metadata import referenced_codes, resolve_course
from app.services.programs import REVIEWED_PROGRAM_IDS, _index


class ProgramGraphError(ValueError):
    def __init__(self, message, code, status):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def find_program(program_id, catalog_term):
    versions = [program for program in _index(None).values() if program["id"] == program_id]
    if not versions:
        raise ProgramGraphError("Unknown program", "unknown_program", 404)
    if catalog_term:
        for program in versions:
            if program["catalogTerm"] == catalog_term:
                return program
        raise ProgramGraphError("The requested program catalog version is unavailable", "catalog_term_unavailable", 404)
    if len(versions) > 1:
        raise ProgramGraphError("Select a catalog term for this program", "catalog_term_required", 400)
    return versions[0]


def group_memberships(program):
    """Map each course code to the requirement groups that can use it, in program order."""
    memberships = {}

    def add(code, group):
        entries = memberships.setdefault(code, [])
        if all(entry["id"] != group["id"] for entry in entries):
            entries.append({"id": group["id"], "label": group["label"], "category": group["category"]})

    def walk(rule, group):
        if rule["type"] == "course":
            add(rule["code"], group)
        if rule.get("courseSet") in program["courseSets"]:
            for code in program["courseSets"][rule["courseSet"]]["codes"]:
                add(code, group)
        for child in rule.get("children", []):
            walk(child, group)

    for group in program["groups"]:
        walk(group["rule"], group)
    return memberships


def prerequisite_links(expression, *, alternative=False):
    """Yield (code, alternative) for every course in an expression. ``alternative`` marks
    courses that sit under an any_of, so one of several choices is enough."""
    if not isinstance(expression, dict):
        return
    kind = expression.get("type")
    if kind == "course" and expression.get("course_code"):
        yield expression["course_code"], alternative
    for child in expression.get("requirements") or []:
        yield from prerequisite_links(child, alternative=alternative or kind == "any_of")


def build_graph(program):
    codes = sorted(referenced_codes(program))
    rows = find_courses(codes)
    memberships = group_memberships(program)
    nodes, edges, outside = [], {}, {}
    known = set(codes)
    for code in codes:
        record = resolve_course(code, program, rows.get(code))
        if record is None:
            nodes.append({"code": code, "title": None, "minimumCredits": None, "maximumCredits": None,
                          "offered": None, "groups": memberships.get(code, []), "metadataSource": None,
                          "prerequisiteState": "unknown", "metadataWarnings": ["course_metadata_unavailable"]})
            continue
        prerequisites = record["prerequisites"]
        nodes.append({"code": code, "title": record["title"], "minimumCredits": record["minimumCredits"],
                      "maximumCredits": record["maximumCredits"], "offered": record["offered"],
                      "groups": memberships.get(code, []), "metadataSource": record["metadataSource"],
                      "prerequisiteState": prerequisites["state"], "metadataWarnings": record["metadataWarnings"]})
        for source, alternative in prerequisite_links(prerequisites["expression"]):
            if source == code:
                continue
            if source in known:
                key = (source, code)
                # A course required outright anywhere in the expression is not optional.
                edges[key] = edges.get(key, True) and alternative
            else:
                outside.setdefault(code, set()).add(source)
    for node in nodes:
        node["outsidePrerequisites"] = sorted(outside.get(node["code"], ()))
    return {
        "program": {"id": program["id"], "name": program["name"], "catalogTerm": program["catalogTerm"],
                    "reviewed": program.get("officialProgramId") in REVIEWED_PROGRAM_IDS},
        "nodes": nodes,
        "edges": [{"source": source, "target": target, "alternative": alternative}
                  for (source, target), alternative in sorted(edges.items())],
    }


def program_graph(program_id, catalog_term=None):
    return build_graph(find_program(program_id, (catalog_term or "").strip() or None))

