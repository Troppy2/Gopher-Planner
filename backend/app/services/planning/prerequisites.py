"""Full prerequisite-tree evaluation. Missing metadata is never treated as no prerequisites."""
import re
from dataclasses import dataclass, field

# Class standing stated in a required prerequisite condition, as earned credits (UMN: sophomore 30,
# junior 60, senior 90). Upper division standing is treated as junior standing.
STANDING = [
    # "CSE lower division or ME upper division", "CSE fr": open to first-year students, so no wait.
    (re.compile(r"\blower[- ]?div|(?<!non-)(?<!non)\b(?:fr|frfy|freshm[ae]n|first[- ]year)\b", re.IGNORECASE), 0),
    (re.compile(r"\b(?:sr|seniors?)\b", re.IGNORECASE), 90),
    (re.compile(r"\b(?:jr|juniors?)\b|\bupper[- ]?div", re.IGNORECASE), 60),
    (re.compile(r"\b(?:soph|sophomores?)\b", re.IGNORECASE), 30),
]
CREDITS = re.compile(r"(?<!max )(?<!than )\b(\d{2,3})\s*(?:\+\s*)?(?:cr|credits?|units)\b", re.IGNORECASE)


def standing_credits(expression):
    """Earned credits a required condition implies ("at least soph", "ME upper div", "60 credits"), or 0.

    Only conditions every route needs count: one inside an ``any_of`` is an alternative, not a rule. When
    a condition names several standings ("jr or sr"), the lowest applies."""
    if not isinstance(expression, dict):
        return 0
    kind = expression.get("type")
    if kind == "condition":
        text = expression.get("text") or ""
        found = [credits for pattern, credits in STANDING if pattern.search(text)]
        found += [int(match.group(1)) for match in CREDITS.finditer(text)]
        return min(found) if found else 0
    if kind == "all_of":
        return max((standing_credits(child) for child in expression.get("requirements") or []), default=0)
    return 0


@dataclass
class PrerequisiteResult:
    ok: bool
    review: bool = False
    unknown: bool = False
    missing: list = field(default_factory=list)


def evaluate_prerequisites(prerequisites, *, done, in_progress, planned, term):
    """``planned`` maps codes to term indexes; only strictly earlier planned terms count, or the same term
    for a course node marked ``concurrent`` (the catalog allows taking it at the same time)."""
    state = (prerequisites or {}).get("state", "unknown")
    if state == "unknown":
        return PrerequisiteResult(False, unknown=True)
    if state == "verified_none" or not prerequisites.get("expression"):
        return PrerequisiteResult(True)

    def walk(node):
        kind = node.get("type")
        if kind == "course":
            code = node.get("course_code")
            limit = term + 1 if node.get("concurrent") else term
            satisfied = code in done or code in in_progress or (code in planned and planned[code] < limit)
            return PrerequisiteResult(satisfied, missing=[] if satisfied else [code])
        if kind in {"all_of", "any_of"}:
            results = [walk(child) for child in node.get("requirements") or []]
            review = any(result.review for result in results)
            if kind == "all_of":
                missing = [code for result in results if not result.ok for code in result.missing]
                return PrerequisiteResult(all(result.ok for result in results), review, missing=missing)
            if any(result.ok for result in results):
                return PrerequisiteResult(True, any(result.review for result in results if result.ok))
            return PrerequisiteResult(False, review, missing=results[0].missing if results else [])
        # Free-text conditions keep their nonblocking behavior but need review.
        return PrerequisiteResult(True, review=True)

    return walk(prerequisites["expression"])
