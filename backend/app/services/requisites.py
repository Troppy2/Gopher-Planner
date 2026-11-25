"""Prerequisite trees for catalog courses, from the most authoritative source available.

Order of precedence for one course:
1. ``reviewed``: a hand-checked tree in ``data/prerequisites/reviewed.json``, written from the enforced
   registration requirement and the catalog text together.
2. ``enforced``: the requirement registration enforces (Schedule Builder), when it parses completely.
3. ``catalog``: the catalog's prerequisite text, when it parses completely.
4. Otherwise a free-text ``condition`` that warns but never blocks, carrying the enforced text when there
   is one so a course with an enforced requirement is never mistaken for one without prerequisites.

Parsing is conservative: text becomes a tree only when every token is a course code, a connector or a
bracket, with one kind of connector per bracket level. Anything else stays text for review.
"""
import csv
import json
import re
from pathlib import Path

TOKEN = re.compile(
    r"\s*(?:(?P<concurrent>concurrent registration (?:is (?:required|allowed)(?: \(or allowed\))? )?in|"
    r"concurrent enrollment in|prereq or concurrent:?|prereq or cc:?)|"
    r"(?P<subject>(?!(?:or|and)\b)[A-Za-z]{2,6})(?=\s*[\[(])|"
    r"(?P<course>(?!(?:or|and)\s)[A-Za-z]{2,6}\s?\d{4}[A-Za-z]?\b)|(?P<number>\d{4}[A-Za-z]?\b)|"
    r"(?P<word>\bor\b|\band\b|&)|(?P<punct>[,;()\[\]]))", re.IGNORECASE)
GRADE = re.compile(r"\s*(?:,\s*)?(?:w/|with (?:a )?)?(?:minimum )?grade of (?:at least )?([A-D][+-]?)(?: or (?:better|higher))?\s*$",
                   re.IGNORECASE)
PREFIX = re.compile(r"^\s*(?:pre-?req(?:uisite)?s?|prerequisites?)\s*:\s*", re.IGNORECASE)
NONE = {"none", "no prerequisites", "no prerequisite"}


class Ambiguous(ValueError):
    pass


def _tokens(text, subject=None, subjects=frozenset()):
    """``subject`` is the course's own subject, which bare numbers refer to; ``subjects`` are known subject
    codes that may stand alone before a bracket ("CSCI [1103 or 1113]")."""
    position, tokens, concurrent = 0, [], False
    while position < len(text):
        match = TOKEN.match(text, position)
        if not match or match.end() == position:
            if text[position:].strip() == "":
                break
            raise Ambiguous(text)
        position = match.end()
        if match.group("concurrent"):
            concurrent = True
            continue
        if match.group("subject"):
            if match.group("subject").upper() not in subjects:
                raise Ambiguous(text)
            subject = match.group("subject").upper()
            continue
        if match.group("course") or match.group("number"):
            if match.group("course"):
                found = re.match(r"([A-Za-z]{2,6})\s?(\d{4}[A-Za-z]?)", match.group("course"))
                subject, digits = found.group(1).upper(), found.group(2).upper()
            elif subject is None:
                raise Ambiguous(text)
            else:
                digits = match.group("number").upper()
            node = {"type": "course", "course_code": f"{subject} {digits}"}
            if concurrent:
                node["concurrent"] = True
            tokens.append(("code", node))
        elif match.group("word"):
            # "concurrent registration in A or B" covers both options; "and" starts a new requirement.
            word = "or" if match.group("word").lower() == "or" else "and"
            concurrent = concurrent and word == "or"
            tokens.append((word, None))
        else:
            punct = match.group("punct")
            if punct in ",;)]":
                concurrent = False
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
            items.append(value)
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


def parse_requisite(text, *, subject=None, subjects=frozenset()):
    """A course tree, a free-text condition, or None for an explicit statement of no prerequisites.

    A trailing minimum grade stays visible as a review condition beside the tree, never as a dropped detail."""
    stripped = PREFIX.sub("", (text or "").strip()).strip().rstrip(".").strip()
    if stripped.lower() in NONE:
        return None
    grade = GRADE.search(stripped)
    body = stripped[:grade.start()].strip() if grade else stripped
    try:
        node, _ = _parse(_tokens(body, subject, subjects), 0, None)
    except Ambiguous:
        return {"type": "condition", "text": (text or "").strip()}
    if grade:
        return {"type": "all_of", "requirements": [node, {"type": "condition", "text": f"Minimum grade {grade.group(1).upper()}"}]}
    return node


def has_condition(node):
    if not isinstance(node, dict):
        return False
    return node.get("type") == "condition" or any(has_condition(child) for child in node.get("requirements") or [])


def load_reviewed(path):
    """``{code: {"expression", "sourceRef", ...}}`` plus the file's ``sources``; empty when no file is given."""
    if not path:
        return {}, {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["courses"], data["sources"]


def load_enforced(path):
    """Distinct enforced requirement texts per course code, newest term first, blank texts omitted."""
    if not path:
        return {}
    csv.field_size_limit(100_000_000)
    by_code = {}
    with open(path, encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            text = " ".join(row["requirement_text"].split())
            entry = by_code.setdefault(" ".join(row["code"].split()),
                                       {"terms": {}, "url": row["source_url"], "retrieved": row["retrieved_at_utc"][:10]})
            entry["terms"].setdefault(row["strm"], [])
            if text and text not in entry["terms"][row["strm"]]:
                entry["terms"][row["strm"]].append(text)
    result = {}
    for code, entry in by_code.items():
        newest = max(entry["terms"])
        result[code] = {"texts": entry["terms"][newest], "strm": newest, "url": entry["url"], "retrieved": entry["retrieved"]}
    return result


def known_only(node, known):
    """Drop options naming courses absent from ``known``; None when a required course is unknown, which
    would otherwise make the course impossible to schedule."""
    if known is None or node.get("type") == "condition":
        return node
    if node["type"] == "course":
        return node if node["course_code"] in known else None
    children = [known_only(child, known) for child in node["requirements"]]
    if node["type"] == "all_of":
        return None if any(child is None for child in children) else {**node, "requirements": children}
    children = [child for child in children if child is not None]
    if not children:
        return None
    return children[0] if len(children) == 1 else {**node, "requirements": children}


def resolve_prerequisites(code, catalog_text, *, enforced=None, reviewed=None, subject=None, subjects=frozenset(),
                          known=None):
    """``(expression, origin, text)``; ``expression`` None with origin ``none`` means no stated prerequisites.

    ``known``, when given, is every catalog course code; a parsed tree naming unknown required courses stays text."""
    if reviewed and code in reviewed:
        entry = reviewed[code]
        return entry["expression"], "reviewed", entry.get("enforced") or entry.get("catalog") or ""
    catalog_text = (catalog_text or "").strip()
    texts = (enforced or {}).get(code, {}).get("texts") or []
    if len(texts) == 1:
        tree = parse_requisite(texts[0], subject=subject, subjects=subjects)
        tree = tree if tree is None else known_only(tree, known)
        if tree is not None and not has_condition(tree):
            return tree, "enforced", texts[0]
    if catalog_text:
        parsed = parse_requisite(catalog_text, subject=subject, subjects=subjects)
        if parsed is None:
            return None, "none", catalog_text
        tree = known_only(parsed, known) or {"type": "condition", "text": catalog_text}
        if not has_condition(tree) or not texts:
            return tree, "catalog", catalog_text
    if texts:
        joined = " | ".join(texts)
        return {"type": "condition", "text": f"Registration requires: {joined}"}, "enforced", joined
    return None, "none", ""
