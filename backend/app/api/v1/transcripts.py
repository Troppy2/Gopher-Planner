from flask import Blueprint, g, request

from app.core.auth import require_auth
from app.extensions import db
from app.extensions.rate_limit import TRANSCRIPT_UPLOAD_LIMIT, limiter, session_or_address
from app.services.transcripts import TranscriptError, serialize_transcript, upload_transcript

transcripts_bp = Blueprint("transcripts", __name__, url_prefix="/api/v1")


def error_response(error):
    db.session.rollback()
    return {"error": error.message, "code": error.code}, error.status


@transcripts_bp.post("/transcripts")
@limiter.limit(TRANSCRIPT_UPLOAD_LIMIT, key_func=session_or_address)
@require_auth
def create_transcript():
    try:
        return {"id": upload_transcript(g.user, request.files.get("file"))}, 201
    except TranscriptError as error:
        return error_response(error)


@transcripts_bp.get("/transcripts/<identity>")
@require_auth
def read_transcript(identity):
    try:
        return serialize_transcript(g.user, identity)
    except TranscriptError as error:
        return error_response(error)

