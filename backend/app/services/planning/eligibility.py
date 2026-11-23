"""Whether a course can be placed in a given future term."""
from dataclasses import dataclass, field

from app.services.planning.prerequisites import evaluate_prerequisites
from app.services.planning.terms import season

INFORMATIONAL = {"offered_terms_unverified", "prerequisites_require_review", "catalog_version_unverified"}


@dataclass
class PlacementCheck:
    ok: bool
    reason: str | None = None
    detail: str | None = None
    warnings: list = field(default_factory=list)


def placement_check(record, term, term_position, *, done, in_progress, planned):
    if record is None:
        return PlacementCheck(False, "course_metadata_unavailable", "unknown_course")
    if record.get("blockedReason"):
        return PlacementCheck(False, "course_metadata_unavailable", record["blockedReason"])
    warnings = [code for code in record.get("metadataWarnings", []) if code in INFORMATIONAL]
    if record.get("offered") is None:
        if "offered_terms_unverified" not in warnings:
            warnings.append("offered_terms_unverified")
    elif season(term) not in record["offered"]:
        return PlacementCheck(False, "not_offered_in_season", season(term))
    result = evaluate_prerequisites(record.get("prerequisites"), done=done, in_progress=in_progress,
                                    planned=planned, term=term_position)
    if result.unknown:
        return PlacementCheck(False, "course_metadata_unavailable", "course_metadata_unavailable")
    if not result.ok:
        return PlacementCheck(False, "prerequisite_not_before", result.missing[0] if result.missing else None)
    if result.review and "prerequisites_require_review" not in warnings:
        warnings.append("prerequisites_require_review")
    return PlacementCheck(True, warnings=warnings)
