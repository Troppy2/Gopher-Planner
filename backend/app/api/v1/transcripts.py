"""APAS upload and the coursework it produces.

POST /api/v1/transcripts            upload an APAS PDF (multipart field "file")
GET  /api/v1/transcripts/<id>       status and counts for one upload
POST /api/v1/transcripts/<id>/ocr   not supported yet (scanned PDFs)
GET  /api/v1/coursework             the signed-in user's course records
"""

import io

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.auth import check_request_origin, read_session
from app.extensions import db
from app.models import CourseRecord, TranscriptUpload
from app.parsers.apas import extract_pdf_text, parse_apas_text
from app.services.coursework import replace_courses, serialize_course_record

transcripts_bp = Blueprint("transcripts", __name__, url_prefix="/api/v1")


def serialize_upload(upload: TranscriptUpload) -> dict:
    # Field names match the frontend's Transcript type.
    return {
        "id": str(upload.id),
        "fileName": upload.file_name,
        "status": upload.status,
        "completed": upload.completed_count,
        "inProgress": upload.in_progress_count,
    }


@transcripts_bp.post("/transcripts")
def upload_transcript():
    origin_error = check_request_origin()
    if origin_error is not None:
        return origin_error

    user_session = read_session()
    if user_session is None:
        return jsonify({"error": "Not signed in"}), 401

    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "Attach a PDF in the 'file' field"}), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    # Read the PDF in memory only; it is never written to disk.
    try:
        text = extract_pdf_text(io.BytesIO(file.read()))
    except Exception:
        current_app.logger.exception("Could not read uploaded PDF")
        text = None

    upload = TranscriptUpload(
        user_id=user_session.user_id,
        file_name=file.filename[:255],
    )

    try:
        if text is None:
            upload.status = "failed"
        elif not text.strip():
            upload.status = "no_text"          # scanned image, no text layer
        else:
            courses = parse_apas_text(text)
            if not courses:
                upload.status = "failed"       # readable, but not an APAS audit
            else:
                upload.completed_count, upload.in_progress_count = replace_courses(
                    user_session.user_id, courses
                )
                upload.status = "parsed"

        db.session.add(upload)
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to save transcript")
        return jsonify({"error": "Transcript service unavailable"}), 503

    return jsonify({"id": str(upload.id)}), 201


@transcripts_bp.get("/transcripts/<int:upload_id>")
def get_transcript(upload_id: int):
    user_session = read_session()
    if user_session is None:
        return jsonify({"error": "Not signed in"}), 401

    upload = db.session.get(TranscriptUpload, upload_id)
    # Someone else's upload looks the same as a missing one.
    if upload is None or upload.user_id != user_session.user_id:
        return jsonify({"error": "Transcript not found"}), 404

    return jsonify(serialize_upload(upload)), 200


@transcripts_bp.post("/transcripts/<int:upload_id>/ocr")
def retry_transcript_ocr(upload_id: int):
    return jsonify({"error": "OCR is not supported yet. Enter courses manually."}), 501


@transcripts_bp.get("/coursework")
def get_coursework():
    user_session = read_session()
    if user_session is None:
        return jsonify({"error": "Not signed in"}), 401

    records = db.session.scalars(
        select(CourseRecord).where(CourseRecord.user_id == user_session.user_id)
    ).all()
    # Chronological order: Spring, Summer, Fall within a year (not alphabetical).
    season_order = {"Spring": 1, "Summer": 2, "Fall": 3}
    records = sorted(records, key=lambda r: (
        r.term_year or 0, season_order.get(r.term_season, 0), r.course_code or ""
    ))

    return jsonify({"courses": [serialize_course_record(r) for r in records]}), 200
