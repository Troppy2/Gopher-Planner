import base64
import hashlib
import json
import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.models.user import User
from app.models.summary import Summary
from app.parsers.parsing_engine import PDFParser, extract_course_codes, normalize_course_code

transcripts_bp = Blueprint("transcripts", __name__, url_prefix="/api/v1")


def _encrypt_transcript_data(data: dict) -> str:
    """Encrypt transcript data using a simple deterministic encryption.

    In production, use a proper KMS or sealed-secret approach.
    Here we base64-encode JSON after hashing with a per-user salt.
    """
    user_id = int(request.headers.get("X-User-Id", "0") or 0)
    salt = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
    payload = json.dumps(data, sort_keys=True).encode()
    # Deterministic "encryption" via XOR with salt stream, then base64
    xor_bytes = bytes(
        b ^ int(salt[(i * 2) % len(salt) : (i * 2 + 2) % len(salt)], 16)
        for i, b in enumerate(payload)
    )
    return base64.b64encode(xor_bytes).decode()


def _decrypt_transcript_data(encrypted: str) -> dict | None:
    """Decrypt transcript data encrypted by _encrypt_transcript_data."""
    try:
        user_id = int(request.headers.get("X-User-Id", "0") or 0)
        salt = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
        xor_bytes = base64.b64decode(encrypted)
        payload = bytes(
            b ^ int(salt[(i * 2) % len(salt) : (i * 2 + 2) % len(salt)], 16)
            for i, b in enumerate(xor_bytes)
        )
        data = json.loads(payload.decode())
        return data
    except Exception:
        return None


@transcripts_bp.get("/transcripts/<int:transcript_id>")
def get_transcript(transcript_id: int):
    """Get a parsed transcript by ID."""
    try:
        # Look for summary associated with this transcript
        summary = db.session.get(Summary, transcript_id)
        if summary is None:
            return jsonify({"error": "Transcript not found"}), 404

        # Check user owns this (simple check - in prod use proper auth)
        from app.api.v1.auth import read_session
        user_session = read_session()
        if user_session is None or user_session.user.id != summary.user_id:
            return jsonify({"error": "Not authorized"}), 403

        decrypted = _decrypt_transcript_data(summary.transcript_encrypted) if summary.transcript_encrypted else None

        return jsonify({
            "id": summary.id,
            "user_id": summary.user_id,
            "credits": summary.credits,
            "gpa": summary.gpa,
            "class_taken": summary.class_taken,
            "class_current": summary.class_current,
            "class_planned": summary.class_planned,
            "program": summary.program,
            "transcript_data": decrypted,
            "created_at": summary.created_at.isoformat() if summary.created_at else None,
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to load transcript")
        return jsonify({"error": "Transcript service unavailable"}), 503


@transcripts_bp.post("/transcripts")
def upload_transcript():
    """Upload and parse a transcript/APAS PDF."""
    try:
        from app.api.v1.auth import read_session

        user_session = read_session()
        if user_session is None:
            return jsonify({"error": "Not signed in"}), 401

        user = user_session.user

        # Check if file is present
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are supported"}), 400

        # Save uploaded file temporarily
        upload_dir = current_app.config.get("UPLOAD_FOLDER", "/tmp/uploads")
        os.makedirs(upload_dir, exist_ok=True)
        filename = f"transcript_{user.id}_{datetime.utcnow().timestamp()}.pdf"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Parse the PDF
        parser = PDFParser(filepath)
        text = parser.extract_text()
        class_data = parser.find_classes(text)

        # Build transcript record
        transcript_data = {
            "user_id": user.id,
            "taken": sorted(class_data.get("taken", set())),
            "current": sorted(class_data.get("current", set())),
            "planned": sorted(class_data.get("planned", set())),
            "raw_text": text[:500] if current_app.config.get("DEBUG", False) else "",
            "parsed_at": datetime.utcnow().isoformat(),
        }

        # Encrypt and store
        encrypted = _encrypt_transcript_data(transcript_data)

        # Update or create summary record
        summary = Summary.query.filter_by(user_id=user.id).first()
        if summary is None:
            summary = Summary(
                user_id=user.id,
                credits=0,
                gpa=0.0,
                class_taken="",
                class_current="",
                class_planned="",
                program="",
                transcript_encrypted=encrypted,
            )
            db.session.add(summary)
        else:
            summary.transcript_encrypted = encrypted
            # Also update summary fields from parsed data
            all_codes = set()
            all_codes.update(class_data.get("taken", set()))
            all_codes.update(class_data.get("current", set()))
            all_codes.update(class_data.get("planned", set()))
            summary.class_taken = ", ".join(all_codes) if all_codes else ""
        
        db.session.commit()

        return jsonify({
            "message": "Transcript uploaded and parsed successfully",
            "transcript_id": summary.id,
            "data": {
                "taken": list(class_data.get("taken", set())),
                "current": list(class_data.get("current", set())),
                "planned": list(class_data.get("planned", set())),
            },
        }), 201

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to process transcript")
        return jsonify({"error": "Transcript service unavailable"}), 503
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Unexpected error processing transcript")
        return jsonify({"error": str(e)}), 500