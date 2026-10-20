
from typing import TypedDict

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token


class GoogleUser(TypedDict):
    id: str
    email: str
    name: str
    picture: str


def verify_google_credential(
    credential: str,
    client_id: str,
) -> GoogleUser:
    claims = id_token.verify_oauth2_token(
        credential,
        Request(),
        audience=client_id,
    )

    google_id = claims.get("sub")
    email = claims.get("email")
    email_verified = claims.get("email_verified")

    if not isinstance(google_id, str) or not google_id:
        raise ValueError("Missing Google user ID")

    if not isinstance(email, str) or not email:
        raise ValueError("Missing email")

    if email_verified is not True:
        raise ValueError("Google email is not verified")

    normalized_email = email.strip().lower()

    if not normalized_email.endswith("@umn.edu"):
        raise PermissionError("Only UMN accounts are allowed")

    return {
        "id": google_id,
        "email": normalized_email,
        "name": str(claims.get("name") or ""),
        "picture": str(claims.get("picture") or ""),
    }
