"""Request rate limits for sign-in and expensive endpoints.

Storage defaults to process memory, so each server worker keeps its own counters and the
effective limit is roughly the per-worker limit times the worker count. Set
RATELIMIT_STORAGE_URI (for example a Redis URL) to share counters between workers.
"""
import hashlib

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Generous per-address limits: many students share a few campus network addresses.
SIGN_IN_LIMIT = "30 per minute;300 per hour"
# Per signed-in session: PDF parsing and OCR are the most expensive requests the API serves.
TRANSCRIPT_UPLOAD_LIMIT = "20 per hour"
PLAN_GENERATE_LIMIT = "60 per hour"


def session_or_address():
    """Key by a hash of the session cookie when present, otherwise by client address."""
    from app.core.auth import COOKIE_NAME  # imported late: app.core.auth imports app.extensions

    token = request.cookies.get(COOKIE_NAME)
    if token:
        return "session:" + hashlib.sha256(token.encode()).hexdigest()[:32]
    return "addr:" + (get_remote_address() or "unknown")


limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
