"""Request rate limits for sign-in and expensive endpoints.

Storage defaults to process memory, so each server worker keeps its own counters and the
effective limit is roughly the per-worker limit times the worker count. Set
RATELIMIT_STORAGE_URI (for example a Redis URL) to share counters between workers.
"""
from flask import g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Generous per-address limits: many students share a few campus network addresses.
SIGN_IN_LIMIT = "30 per minute;300 per hour"
# Per signed-in user: PDF parsing and OCR are the most expensive requests the API serves.
TRANSCRIPT_UPLOAD_LIMIT = "20 per hour"
PLAN_GENERATE_LIMIT = "60 per hour"


def user_or_address():
    """Key by the signed-in user, so extra sessions or invented cookies share one budget.

    Requests without a valid session fall back to the client address."""
    from app.core.auth import read_session  # imported late: app.core.auth imports app.extensions

    if "rate_limit_user" not in g:
        session = read_session()
        g.rate_limit_user = session.user_id if session else None
    if g.rate_limit_user is not None:
        return f"user:{g.rate_limit_user}"
    return "addr:" + (get_remote_address() or "unknown")


limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
