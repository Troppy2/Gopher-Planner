"""Full prerequisite-tree evaluation. Missing metadata is never treated as no prerequisites."""
from dataclasses import dataclass, field


@dataclass
class PrerequisiteResult:
    ok: bool
    review: bool = False
    unknown: bool = False
    missing: list = field(default_factory=list)


def evaluate_prerequisites(prerequisites, *, done, in_progress, planned, term):
    """``planned`` maps codes to term indexes; only strictly earlier planned terms count."""
    state = (prerequisites or {}).get("state", "unknown")
    if state == "unknown":
        return PrerequisiteResult(False, unknown=True)
    if state == "verified_none" or not prerequisites.get("expression"):
        return PrerequisiteResult(True)

    def walk(node):
        kind = node.get("type")
        if kind == "course":
            code = node.get("course_code")
            satisfied = code in done or code in in_progress or (code in planned and planned[code] < term)
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
