"""Owner-filtered persistence for each user's single plan."""
from sqlalchemy import delete, select

from app.extensions import db
from app.models import Plan, PlanCourse


def find_plan(user_id):
    return db.session.scalar(select(Plan).where(Plan.user_id == user_id))


def get_or_create_plan(user_id):
    plan = find_plan(user_id)
    if plan is None:
        plan = Plan(user_id=user_id)
        db.session.add(plan)
        db.session.flush()
    return plan


def planned_courses(user_id):
    """Map code to (term, source) for the user's plan only."""
    rows = db.session.execute(
        select(PlanCourse.code, PlanCourse.term, PlanCourse.source)
        .join(Plan, Plan.id == PlanCourse.plan_id).where(Plan.user_id == user_id).order_by(PlanCourse.code))
    return {code: (term, source) for code, term, source in rows}


def planned_slots(user_id):
    """Map code to its sample-plan slot label for planned courses that fill one."""
    rows = db.session.execute(
        select(PlanCourse.code, PlanCourse.slot)
        .join(Plan, Plan.id == PlanCourse.plan_id).where(Plan.user_id == user_id, PlanCourse.slot.is_not(None)))
    return dict(rows.all())


def replace_planned_courses(user_id, courses, *, catalog_term=None, set_term=False, generated_at=None, slots=None):
    """Replace every planned course for this user inside the caller's transaction.

    ``slots`` maps codes to slot labels; when omitted, a course that stays planned keeps its label."""
    if slots is None:
        slots = planned_slots(user_id)
    plan = get_or_create_plan(user_id)
    if set_term:
        plan.catalog_term = catalog_term
    if generated_at is not None:
        plan.generated_at = generated_at
    db.session.execute(delete(PlanCourse).where(PlanCourse.plan_id == plan.id))
    for code, (term, source) in sorted(courses.items()):
        db.session.add(PlanCourse(plan_id=plan.id, code=code, term=term, source=source, slot=slots.get(code)))
    return plan
