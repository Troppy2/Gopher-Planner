"""Create a sign-in session without Google, for local testing and demos.

    uv run python scripts/dev_session.py you@umn.edu

Prints a session token. Send it as the gp_session cookie, e.g.
    curl --cookie "gp_session=<token>" http://localhost:5000/api/v1/summary

Refuses to run when FLASK_ENVIRONMENT=production.
"""

import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app import create_app  # noqa: E402
from app.api.v1.auth import hash_session_token  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User, UserSession  # noqa: E402


def main() -> None:
    if os.getenv("FLASK_ENVIRONMENT", "development").lower() == "production":
        sys.exit("Refusing to create a dev session in production.")
    if len(sys.argv) != 2 or not sys.argv[1].endswith("@umn.edu"):
        sys.exit("Usage: uv run python scripts/dev_session.py you@umn.edu")

    email = sys.argv[1]
    with create_app().app_context():
        user = db.session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(google_sub=f"dev:{email}", email=email, name=email.split("@")[0])
            db.session.add(user)
            db.session.flush()

        token = secrets.token_urlsafe(32)
        db.session.add(UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
        ))
        db.session.commit()
        print(token)


if __name__ == "__main__":
    main()
