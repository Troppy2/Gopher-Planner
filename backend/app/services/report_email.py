"""Email each saved report to the maintainers.

Configured entirely by environment variables, so no address or credential lives in the repo:

    REPORT_NOTIFY_EMAIL   comma-separated recipients; unset disables email
    SMTP_HOST, SMTP_PORT  for example smtp.gmail.com and 587 (STARTTLS) or 465 (SSL)
    SMTP_USERNAME, SMTP_PASSWORD
    SMTP_FROM             sender address; defaults to SMTP_USERNAME

Sending happens on a background thread after the report is committed, so a slow or failing
mail server never delays the student or loses the report. Failures are logged without the
report's note or any recipient address.
"""
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage

from flask import current_app

REASON_LABELS = {
    "prerequisites_wrong": "The prerequisites are wrong",
    "offered_terms_wrong": "It's offered in different terms",
    "details_wrong": "The title, credits, or description is wrong",
    "missing_course": "A course that counts is missing",
    "course_should_not_count": "A course listed here doesn't count",
    "rule_wrong": "The number of courses or credits is wrong",
    "other": "Something else",
}


def email_settings():
    recipients = [part.strip() for part in os.getenv("REPORT_NOTIFY_EMAIL", "").split(",") if part.strip()]
    host = os.getenv("SMTP_HOST", "").strip()
    if not recipients or not host:
        return None
    username = os.getenv("SMTP_USERNAME", "").strip()
    return {
        "recipients": recipients, "host": host, "port": int(os.getenv("SMTP_PORT", "587") or 587),
        "username": username, "password": os.getenv("SMTP_PASSWORD", ""),
        "sender": os.getenv("SMTP_FROM", "").strip() or username,
    }


def build_message(report, *, created, sender, recipients):
    """A plain-text email describing one report. Never includes the student's identity."""
    if report["targetType"] == "course":
        target = f"Course {report['courseCode']}"
    else:
        target = (f"Requirement group {report['requirementId']} in {report.get('programId') or 'unknown program'}, "
                  f"catalog year {report.get('catalogTerm') or 'unknown'}")
    message = EmailMessage()
    message["Subject"] = f"[Gopher Planner] {'New' if created else 'Updated'} report: {target}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content("\n".join([
        f"{'A student reported' if created else 'A student updated their report about'} a problem.",
        "",
        f"What: {target}",
        f"Reason: {REASON_LABELS.get(report['reason'], report['reason'])}",
        f"Note: {report['note'] or '(none)'}",
        "",
        f"Report #{report['id']}, submitted {report['createdAt']}, updated {report['updatedAt']}.",
        "Review open reports with: uv run python scripts/report_summary.py --notes",
    ]))
    return message


def _send(settings, message, report_id, logger):
    try:
        if settings["port"] == 465:
            server = smtplib.SMTP_SSL(settings["host"], settings["port"], timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(settings["host"], settings["port"], timeout=15)
        with server:
            if settings["port"] != 465:
                server.starttls(context=ssl.create_default_context())
            if settings["username"]:
                server.login(settings["username"], settings["password"])
            server.send_message(message)
    except Exception as error:  # noqa: BLE001 - email is best effort; the report is already saved
        logger.error("Report email failed (%s), report id=%s", type(error).__name__, report_id)


def notify_report(report, *, created, wait=False):
    """Email a serialized report to the maintainers if email is configured. Returns the thread, if any."""
    settings = email_settings()
    if settings is None:
        return None
    message = build_message(report, created=created, sender=settings["sender"], recipients=settings["recipients"])
    # The app logger is captured here because the send thread has no application context.
    logger = current_app.logger
    thread = threading.Thread(target=_send, args=(settings, message, report["id"], logger), daemon=True)
    thread.start()
    if wait:
        thread.join()
    return thread
