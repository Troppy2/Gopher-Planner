from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from app.core.auth import check_request_origin, read_session
from app.extensions import db
from app.services import reports
from app.services.report_email import notify_report
from app.extensions.rate_limit import REPORT_LIMIT, limiter, user_or_address

reports_bp = Blueprint("reports", __name__, url_prefix="/api/v1")


@reports_bp.get("/reports")
def get_reports():
    try:
        session = read_session()
        if session is None:
            return jsonify(error="Not signed in"), 401
        rows = reports.get_reports(session.user_id)
        # Independently enforce the authenticated owner at the route boundary.
        return jsonify(reports=[reports.serialize_report(row) for row in rows if row.user_id == session.user_id])
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error("Report read failed")
        return jsonify(error="Report service unavailable"), 503


@reports_bp.post("/reports")
@limiter.limit(REPORT_LIMIT, key_func=user_or_address)
def create_report():
    origin_error = check_request_origin()
    if origin_error is not None:
        return origin_error
    report_id = None
    try:
        session = read_session()
        if session is None:
            return jsonify(error="Not signed in"), 401
        row, created = reports.create_report(session.user_id, request.get_json(silent=True))
        if row.user_id != session.user_id:
            db.session.rollback()
            return jsonify(error="Not signed in"), 401
        report_id = row.id
        result = reports.serialize_report(row)
        target = {"programId": row.program_id, "catalogTerm": row.catalog_term}
        db.session.commit()
        # After commit and on its own thread: email never delays or undoes a saved report.
        notify_report({**result, **target}, created=created)
        return jsonify(result), 201 if created else 200
    except reports.ReportError as error:
        db.session.rollback()
        return jsonify(error=error.message, code=error.code), error.status
    except SQLAlchemyError as error:
        db.session.rollback()
        # SQLAlchemy exception strings and tracebacks can include bound note values.
        # Log a fixed message and exception type only, never SQL or parameters.
        current_app.logger.error("Report write failed (%s), report id=%s", type(error).__name__, report_id)
        return jsonify(error="Report service unavailable"), 503
