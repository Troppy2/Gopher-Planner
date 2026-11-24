"""Report emails: configured only by environment, sent after commit, never fatal. Synthetic data."""
import pytest

from app.services import report_email


@pytest.fixture(autouse=True)
def synthetic_programs(program_files):
    pass


class FakeSMTP:
    sent = []
    fail = False

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        pass

    def login(self, username, password):
        self.username = username

    def send_message(self, message):
        if FakeSMTP.fail:
            raise OSError("synthetic outage")
        FakeSMTP.sent.append(message)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.sent, FakeSMTP.fail = [], False
    monkeypatch.setattr(report_email.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(report_email.smtplib, "SMTP_SSL", FakeSMTP)
    # Run the send inline so tests can assert on it.
    original = report_email.notify_report
    monkeypatch.setattr("app.api.v1.reports.notify_report", lambda report, created: original(report, created=created, wait=True))
    return FakeSMTP


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("REPORT_NOTIFY_EMAIL", "maintainer@example.invalid")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setenv("SMTP_USERNAME", "sender@example.invalid")
    monkeypatch.setenv("SMTP_PASSWORD", "synthetic")


def report(client, headers, **extra):
    body = dict(targetType="course", courseCode="CSCI 1001", reason="prerequisites_wrong", **extra)
    return client.post("/api/v1/reports", json=body, headers=headers)


def test_new_report_is_emailed_without_the_students_identity(client, make_user, login_as, post_headers, catalog, smtp, configured):
    login_as(make_user(email="synthetic-student@example.invalid"))
    assert report(client, post_headers, note="Synthetic note").status_code == 201
    (message,) = smtp.sent
    assert message["To"] == "maintainer@example.invalid"
    assert message["From"] == "sender@example.invalid"
    assert message["Subject"] == "[Gopher Planner] New report: Course CSCI 1001"
    body = message.get_content()
    assert "The prerequisites are wrong" in body and "Synthetic note" in body
    assert "synthetic-student@example.invalid" not in body


def test_updated_report_says_updated(client, make_user, login_as, post_headers, catalog, smtp, configured):
    login_as(make_user())
    report(client, post_headers)
    assert report(client, post_headers, note="More detail").status_code == 200
    assert smtp.sent[-1]["Subject"].startswith("[Gopher Planner] Updated report")


def test_no_email_without_configuration(client, make_user, login_as, post_headers, catalog, smtp, monkeypatch):
    monkeypatch.delenv("REPORT_NOTIFY_EMAIL", raising=False)
    login_as(make_user())
    assert report(client, post_headers).status_code == 201
    assert smtp.sent == []


def test_mail_failure_keeps_the_report_and_logs_no_note(app, client, make_user, login_as, post_headers, catalog, smtp, configured, monkeypatch):
    logged = []
    monkeypatch.setattr(app.logger, "error", lambda message, *args: logged.append(message % args))
    smtp.fail = True
    login_as(make_user())
    assert report(client, post_headers, note="Private synthetic note").status_code == 201
    assert len(client.get("/api/v1/reports").json["reports"]) == 1
    (line,) = logged
    assert line.startswith("Report email failed (OSError)")
    assert "Private synthetic note" not in line and "maintainer@example.invalid" not in line


def test_requirement_email_names_program_and_catalog_year(client, make_user, login_as, post_headers, smtp, configured):
    from app.extensions import db
    from app.models import Plan
    user = make_user()
    user.major = "Synthetic B.S."
    db.session.add(Plan(user_id=user.id, catalog_term="Fall 2026"))
    db.session.commit()
    login_as(user)
    body = dict(targetType="requirement", requirementId="core", reason="missing_course")
    assert client.post("/api/v1/reports", json=body, headers=post_headers).status_code == 201
    subject = smtp.sent[-1]["Subject"]
    assert "Requirement group core" in subject and "catalog year Fall 2026" in subject
