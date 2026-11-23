from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.parametrize("claims,status,error", [
    ({"sub": "synthetic", "email": "synthetic@example.invalid", "email_verified": True}, 403,
     "Only verified @umn.edu accounts can sign in"),
    ({"sub": "synthetic", "email": "synthetic@umn.edu", "email_verified": False}, 401,
     "Invalid Google credential"),
])
def test_google_login_rejects_ineligible_claims(client, monkeypatch, post_headers, claims, status, error):
    monkeypatch.setattr("app.core.google_auth.id_token.verify_oauth2_token", lambda *a, **kw: claims)
    response = client.post("/api/v1/auth/google", json={"credential": "synthetic"}, headers=post_headers)
    assert response.status_code == status
    assert response.json == ({"error": error, "code": "not_umn"} if status == 403 else {"error": error})


@pytest.mark.parametrize("state", ["expired", "revoked"])
def test_inactive_session_is_rejected(client, make_user, login_as, state):
    now = datetime.now(timezone.utc)
    login_as(make_user(), **(
        {"expires_at": now - timedelta(seconds=1)} if state == "expired"
        else {"revoked_at": now}
    ))
    response = client.get("/api/v1/profile")
    assert response.status_code == 401
    assert response.json == {"error": "Not signed in"}


@pytest.mark.parametrize("path,method", [("/auth/google", "post"), ("/auth/logout", "post"), ("/profile", "put")])
def test_state_changes_reject_wrong_origin(client, make_user, login_as, path, method):
    login_as(make_user())
    response = getattr(client, method)("/api/v1" + path, json={}, headers={"Origin": "http://untrusted.invalid"})
    assert response.status_code == 403
    assert response.json == {"error": "Untrusted request origin"}


@pytest.mark.parametrize("body,message", [
    ({"creditLoad": True}, "creditLoad must be an integer"),
    ({"creditLoad": 0}, "creditLoad must be between 1 and 30"),
    ({"creditLoad": 31}, "creditLoad must be between 1 and 30"),
    ({"name": 1}, "name must be a string"),
    ({"name": "x" * 256}, "name must be at most 255 characters"),
    ({"onboarded": "yes"}, "onboarded must be a boolean"),
    ({"unknown": "x"}, "Unknown profile fields"),
])
def test_profile_rejects_invalid_fields_atomically(client, make_user, login_as, post_headers, body, message):
    login_as(make_user())
    before = client.get("/api/v1/profile").json
    response = client.put("/api/v1/profile", json=body, headers=post_headers)
    assert response.status_code == 400
    assert response.json["error"] == message
    assert client.get("/api/v1/profile").json == before


def test_profile_rejects_blank_name_without_overwriting_saved_name(client, make_user, login_as, post_headers):
    """Onboarding and Settings both require a name containing non-whitespace."""
    login_as(make_user())
    saved = client.put("/api/v1/profile", json={"name": "Synthetic name"}, headers=post_headers)
    assert saved.status_code == 200
    response = client.put("/api/v1/profile", json={"name": "   "}, headers=post_headers)
    assert response.status_code == 400
    assert client.get("/api/v1/profile").json["name"] == "Synthetic name"


def test_session_expires_at_injected_clock_boundary(client, make_user, login_as, clock):
    expiry = clock["now"] + timedelta(minutes=5)
    login_as(make_user(), expires_at=expiry)
    assert client.get("/api/v1/profile").status_code == 200
    clock["now"] = expiry
    assert client.get("/api/v1/profile").status_code == 401
