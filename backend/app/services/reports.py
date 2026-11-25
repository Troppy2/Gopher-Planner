"""Validation and owner-scoped report collection. Never modifies academic data."""
from datetime import timedelta
from sqlalchemy import func, select

from app.extensions import db
from app.models import DataReport
from app.models.user import utc_now
from app.repositories.catalog import course_exists
from app.repositories.locks import lock_user
from app.schemas.coursework import CODE_PATTERN
from app.services.plan import resolve_context

REPORT_REASONS = {
    "course": ("prerequisites_wrong", "offered_terms_wrong", "details_wrong", "other"),
    "requirement": ("missing_course", "course_should_not_count", "rule_wrong", "other"),
}


class ReportError(Exception):
    def __init__(self, status=400, code="invalid_report", message="Invalid report"):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def validate_report(body):
    if not isinstance(body, dict):
        raise ReportError()
    target = body.get("targetType")
    if not isinstance(target, str) or target not in REPORT_REASONS:
        raise ReportError()
    field = "courseCode" if target == "course" else "requirementId"
    if set(body) - {"targetType", field, "reason", "note"}:
        raise ReportError()
    if not isinstance(body.get("reason"), str) or body["reason"] not in REPORT_REASONS[target]:
        raise ReportError()
    value = body.get(field)
    if not isinstance(value, str) or not value:
        raise ReportError()
    if target == "course" and not CODE_PATTERN.fullmatch(value):
        raise ReportError()
    if target == "requirement" and len(value) > 64:
        raise ReportError()
    note = body.get("note", "")
    if not isinstance(note, str) or len(note) > 500:
        raise ReportError()
    return target, value, body["reason"], note.strip() or None


def get_reports(user_id):
    return db.session.scalars(select(DataReport).where(
        DataReport.user_id == user_id, DataReport.status == "open"
    ).order_by(DataReport.created_at.desc(), DataReport.id.desc())).all()


def create_report(user_id, body):
    target, value, reason, note = validate_report(body)
    user = lock_user(user_id)
    if user is None:
        raise ReportError(401, "unauthorized", "Not signed in")
    fields = dict(target_type=target)
    context = resolve_context(user)
    if target == "course":
        metadata = context.program.get("courseMetadata", {}) if context.program else {}
        if not course_exists(value) and value not in metadata:
            raise ReportError()
        fields["course_code"] = value
    else:
        if context.program is None or context.catalog_term is None:
            raise ReportError(400, "program_version_unconfirmed", "Confirm your program catalog year first")
        if value not in {group["id"] for group in context.program["groups"]}:
            raise ReportError()
        fields.update(program_id=context.program["id"], catalog_term=context.catalog_term, requirement_id=value)
    existing = db.session.scalar(select(DataReport).filter_by(
        user_id=user.id, status="open", **fields))
    created = existing is None
    if created:
        count = db.session.scalar(select(func.count()).select_from(DataReport).where(
            DataReport.user_id == user.id, DataReport.created_at >= utc_now() - timedelta(hours=24)))
        if count >= 20:
            raise ReportError(429, "report_limit", "Daily report limit reached")
        existing = DataReport(user_id=user.id, **fields)
        db.session.add(existing)
    existing.reason, existing.note = reason, note
    existing.updated_at = utc_now()
    db.session.flush()
    return existing, created


def serialize_report(report):
    return {
        "id": report.id, "targetType": report.target_type, "courseCode": report.course_code,
        "requirementId": report.requirement_id, "reason": report.reason, "note": report.note,
        "status": report.status, "createdAt": report.created_at.isoformat(), "updatedAt": report.updated_at.isoformat(),
    }
