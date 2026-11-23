"""Synchronous transcript import. Scanned PDFs are read with local OCR. The PDF and its text are
never stored or logged; only parsed rows are."""
import json
import logging
import re
from uuid import uuid4

from sqlalchemy import delete, select

from app.extensions import db
from app.models import CatalogCourse, Coursework, Transcript
from app.parsers.ocr import ocr_pdf_text
from app.parsers.pdf_text import PdfUnreadable, extract_pdf_text
from app.parsers.transcript import parse_apas_le, parse_apas_text, parse_transcript_text
from app.repositories.locks import lock_user

logger = logging.getLogger(__name__)


class TranscriptError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def sanitize_file_name(name):
    base = re.split(r"[\\/]", name or "")[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base).replace("..", "").strip(" .")
    return (base or "transcript.pdf")[:255]


def owned_transcript(user, identity):
    transcript = db.session.scalar(select(Transcript).where(Transcript.id == identity, Transcript.user_id == user.id))
    if transcript is None:
        raise TranscriptError(404, "not_found", "Transcript not found")
    return transcript


PLACEHOLDER = re.compile(r"^(?:NOTR \S+|[A-Z]{2,6} \d[A-Z]\d{3}[A-Z]?|[A-Z]{2,6} \d{4}[A-Z]?)$")


def _parse(text, known_codes):
    """APAS audit rows first, then the generic one-row-per-course layout."""
    rows, skipped = parse_apas_text(text, known_codes=known_codes)
    if rows:
        return rows, skipped
    return parse_transcript_text(text), []


def _looks_misread(skipped, known_codes):
    """Transfer placeholders (HUM 1T001, NOTR ...) and zero-credit rows are expected; anything else
    skipped, or a subject the catalog does not know, means the text layer likely came from a poor OCR pass."""
    subjects = {code.split(" ")[0] for code in known_codes} if known_codes else None
    return any(not PLACEHOLDER.match(code) or (subjects and code.split(" ")[0] not in subjects | {"NOTR"})
               for code in skipped)


def _better(first, second):
    """Prefer more imported courses, then fewer unreadable codes."""
    return max(first, second, key=lambda result: (len(result[0]), -len(result[1])))


def upload_transcript(user, file):
    if file is None or not file.filename:
        raise TranscriptError(400, "missing_file", "Upload a PDF in the file field")
    data = file.read()
    if not data.startswith(b"%PDF"):
        raise TranscriptError(415, "not_a_pdf", "Only PDF files are accepted")
    identity, user_id = str(uuid4()), user.id
    db.session.add(Transcript(id=identity, user_id=user_id, file_name=sanitize_file_name(file.filename), status="parsing"))
    db.session.commit()
    known_codes = set(db.session.scalars(select(CatalogCourse.course_code))) or None  # None: catalog not loaded
    db.session.close()  # never hold a database session across parsing
    status, error_code, rows, skipped, liberal = "parsed", None, [], [], None
    try:
        text = extract_pdf_text(data)
        rows, skipped = _parse(text, known_codes)
        liberal = parse_apas_le(text)
        if not rows or _looks_misread(skipped, known_codes):
            # Image-only scans, or scans whose text layer came from a poor OCR pass: read the pages ourselves.
            ocr_text = ocr_pdf_text(data)
            if ocr_text.strip():
                rows, skipped = _better(_parse(ocr_text, known_codes), (rows, skipped))
                recognized = parse_apas_le(ocr_text)
                if recognized and (not liberal or len(recognized[0]) > len(liberal[0])):
                    liberal = recognized  # the read that found more category headings
                text = text if text.strip() else ocr_text
        if not text.strip():
            status = "no_text"
        elif not rows:
            status, error_code = "failed", "unrecognized_format"
    except PdfUnreadable:
        status, error_code = "failed", "unreadable_pdf"
        logger.info("Transcript %s could not be read", identity)
    except Exception:  # noqa: BLE001 - never leave a transcript parsing forever
        status, error_code, rows, skipped = "failed", "parse_error", [], []
        # Only the ID: exception messages could quote document text.
        logger.error("Transcript %s parsing failed unexpectedly", identity)
    finally:
        del data
    lock_user(user_id)
    transcript = db.session.get(Transcript, identity)
    transcript.status, transcript.error_code = status, error_code
    transcript.not_imported = json.dumps(skipped) if status == "parsed" else None
    keep = status == "parsed" and liberal is not None
    transcript.le_required = json.dumps(sorted(liberal[0])) if keep else None
    transcript.le_covered = json.dumps(sorted(liberal[1])) if keep else None
    if status == "parsed":
        db.session.execute(delete(Coursework).where(Coursework.user_id == user_id, Coursework.source == "transcript"))
        manual = {(code, term) for code, term in db.session.execute(
            select(Coursework.code, Coursework.term).where(Coursework.user_id == user_id))}
        for row in rows:
            key = (row["code"], row["term"])
            if key in manual:
                continue  # a manual entry for the same attempt is kept
            manual.add(key)
            db.session.add(Coursework(user_id=user_id, source="transcript", transcript_id=identity, **row))
    db.session.commit()
    return identity


def serialize_transcript(user, identity):
    from app.services.coursework import serialize_coursework

    transcript = owned_transcript(user, identity)
    rows = db.session.scalars(select(Coursework).where(Coursework.user_id == user.id, Coursework.transcript_id == identity)
                              .order_by(Coursework.code, Coursework.term)).all()
    body = {"id": transcript.id, "fileName": transcript.file_name, "status": transcript.status,
            "completed": sum(row.status == "done" for row in rows), "inProgress": sum(row.status == "prog" for row in rows),
            "courses": [serialize_coursework(row) for row in rows]}
    body["notImported"] = json.loads(transcript.not_imported) if transcript.not_imported else []
    if transcript.error_code:
        body["errorCode"] = transcript.error_code
    return body
