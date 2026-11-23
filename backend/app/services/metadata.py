"""Version-aware course metadata selection across the read-only catalog and program supplements.

Precedence for a selected program version:
1. A catalog record whose release is mapped by the program's sourced ``catalogCompatibility``.
   If a matching supplemental record disagrees, both remain visible but placement is blocked.
2. Target-version supplemental metadata from the program file.
3. Unknown-version or unmapped legacy catalog facts, flagged ``catalog_version_unverified``.
"""
import copy
import re

SEASONS = ("Fall", "Spring", "Summer")
CODE = re.compile(r"^([A-Za-z]{2,6}) ?(\d{4}[A-Za-z]?)$")


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
