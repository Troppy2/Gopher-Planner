def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_profile_requires_a_session(client):
    response = client.get("/api/v1/profile")
    assert response.status_code == 401
    assert response.json == {"error": "Not signed in"}


def test_unknown_route_returns_json_error(client):
    response = client.get("/api/v1/unknown")
    assert response.status_code == 404
    assert response.is_json
    assert set(response.json) == {"error", "code"}
    assert response.json["code"] == "not_found"


def test_courses_require_a_session(client):
    response = client.get("/api/v1/courses")
    assert response.status_code == 401
    assert response.json == {"error": "Not signed in"}


def test_summary_requires_a_session(client):
    response = client.get("/api/v1/summary")
    assert response.status_code == 401
    assert response.json == {"error": "Not signed in"}


def test_wrong_method_returns_json_error_with_allow_header(client):
    response = client.post("/health")
    assert response.status_code == 405
    assert response.is_json
    assert set(response.json) == {"error", "code"}
    assert response.json["code"] == "method_not_allowed"
    assert "GET" in response.headers["Allow"]


def test_oversized_request_returns_json_413(app, client):
    from flask import request

    @app.post("/_test/body")
    def consume_body():
        request.get_data()
        return {}

    response = client.post("/_test/body", data=b"x" * (10 * 1024 * 1024 + 1))
    assert response.status_code == 413
    assert response.json["code"] == "too_large"
    assert isinstance(response.json["error"], str)


def test_unhandled_exception_returns_json_and_logs_stack_without_body(app, client, caplog):
    import logging

    @app.post("/_test/failure")
    def fail():
        raise RuntimeError("Synthetic failure")

    app.config["PROPAGATE_EXCEPTIONS"] = False
    with caplog.at_level(logging.ERROR, logger=app.logger.name):
        response = client.post("/_test/failure", data="synthetic-private-body-marker")
    assert response.status_code == 500
    assert response.is_json
    assert response.json == {"error": "Internal server error", "code": "internal_error"}
    assert any(record.exc_info for record in caplog.records)
    assert "synthetic-private-body-marker" not in caplog.text
    assert "Synthetic failure" not in response.get_data(as_text=True)
