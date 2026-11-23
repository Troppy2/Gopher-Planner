"""Whole-plan schedule validation used by plan saves. Degree incompleteness is not a violation."""
from app.services.planning.eligibility import placement_check


def validate_plan(planned, *, locked, metadata, terms, changed=frozenset()):
    """``planned`` maps codes to future terms; ``locked`` maps done/prog codes to their status."""
    violations = [{"code": code, "reason": "locked_course", "detail": locked[code]} for code in sorted(changed) if code in locked]
    done = {code for code, status in locked.items() if status == "done"}
    in_progress = {code for code, status in locked.items() if status == "prog"}
    positions = {code: terms.index(term) for code, term in planned.items() if code not in locked}
    for code in sorted(positions, key=lambda value: (positions[value], value)):
        others = {other: index for other, index in positions.items() if other != code}
        check = placement_check(metadata.get(code), planned[code], positions[code], done=done, in_progress=in_progress, planned=others)
        if not check.ok:
            violations.append({"code": code, "reason": check.reason, "detail": check.detail})
    return violations
