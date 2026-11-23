"""Transcript upload pipeline with generated synthetic PDFs. Never uses real transcripts."""
import io
import logging
import tempfile
from pathlib import Path

import pytest

MARKER = "SYNTHETICPRIVATEMARKER"


def pdf(lines=(), *, blank=False):
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    if not blank:
        y = 800
        for line in lines:
            page.drawString(40, y, line)
            y -= 16
    page.showPage()
    page.save()
    return buffer.getvalue()


TRANSCRIPT = [f"{MARKER} Student Record", "Fall 2025", "CSCI 1133  Introduction to Computing  4.0  A-",
              "MATH 1271  Calculus I  4.0  B", "Spring 2026", "CSCI 1933  Data Structures  4.0  IP"]


def upload(client, headers, data, name="apas.pdf"):
    return client.post("/api/v1/transcripts", data={"file": (io.BytesIO(data), name)}, headers=headers,
                       content_type="multipart/form-data")


def test_pdf_wrapper_returns_plain_text_separately_from_the_parser():
    from app.parsers.pdf_text import extract_pdf_text
    assert "CSCI 1133" in extract_pdf_text(pdf(TRANSCRIPT))
    assert extract_pdf_text(pdf(blank=True)).strip() == ""


def test_valid_pdf_is_parsed_into_transcript_coursework(client, make_user, login_as, post_headers):
    login_as(make_user())
    response = upload(client, post_headers, pdf(TRANSCRIPT))
    assert response.status_code == 201
    transcript = client.get(f"/api/v1/transcripts/{response.json['id']}").json
    assert (transcript["status"], transcript["completed"], transcript["inProgress"], transcript["fileName"]) == ("parsed", 2, 1, "apas.pdf")
    assert {course["code"] for course in transcript["courses"]} == {"CSCI 1133", "MATH 1271", "CSCI 1933"}
    stored = client.get("/api/v1/coursework").json["courses"]
    assert {course["source"] for course in stored} == {"transcript"}


def test_image_only_or_blank_pdf_reports_no_text(client, make_user, login_as, post_headers, monkeypatch):
    monkeypatch.setattr("app.services.transcripts.ocr_pdf_text", lambda data: "")
    login_as(make_user())
    identity = upload(client, post_headers, pdf(blank=True)).json["id"]
    assert client.get(f"/api/v1/transcripts/{identity}").json["status"] == "no_text"


def test_text_without_recognizable_rows_fails_with_a_reason(client, make_user, login_as, post_headers):
    login_as(make_user())
    identity = upload(client, post_headers, pdf(["A synthetic letter with no course rows"])).json["id"]
    transcript = client.get(f"/api/v1/transcripts/{identity}").json
    assert (transcript["status"], transcript["errorCode"], transcript["courses"]) == ("failed", "unrecognized_format", [])


def test_upload_rejects_missing_non_pdf_and_oversized_files(client, make_user, login_as, post_headers):
    login_as(make_user())
    missing = client.post("/api/v1/transcripts", data={}, headers=post_headers, content_type="multipart/form-data")
    assert (missing.status_code, missing.json["code"]) == (400, "missing_file")
    not_pdf = upload(client, post_headers, b"hello, not a pdf")
    assert (not_pdf.status_code, not_pdf.json["code"]) == (415, "not_a_pdf")
    large = upload(client, post_headers, b"%PDF" + b"0" * (10 * 1024 * 1024))
    assert (large.status_code, large.json["code"]) == (413, "too_large")


def test_reupload_replaces_transcript_rows_and_keeps_manual_rows(client, make_user, login_as, post_headers):
    login_as(make_user())
    manual = {"code": "WRIT 1301", "title": "Writing", "credits": 3, "status": "done", "grade": "A", "term": "Fall 2025"}
    upload(client, post_headers, pdf(TRANSCRIPT))
    current = client.get("/api/v1/coursework").json["courses"]
    client.put("/api/v1/coursework", json={"courses": [*current, manual], "skipped": False}, headers=post_headers)
    upload(client, post_headers, pdf(["Fall 2025", "STAT 3021  Statistics  3.0  A", "WRIT 1301  Writing again  3.0  B"]))
    stored = {(course["code"], course["source"]) for course in client.get("/api/v1/coursework").json["courses"]}
    assert stored == {("STAT 3021", "transcript"), ("WRIT 1301", "manual")}


def test_ocr_runs_at_upload_so_there_is_no_retry_route_and_other_users_transcripts_are_not_found(
        client, make_user, login_as, post_headers):
    login_as(make_user())
    identity = upload(client, post_headers, pdf(blank=True)).json["id"]
    assert client.post(f"/api/v1/transcripts/{identity}/ocr", headers=post_headers).status_code in {404, 405}
    login_as(make_user())
    assert client.get(f"/api/v1/transcripts/{identity}").status_code == 404
    assert client.get("/api/v1/transcripts/not-a-real-id").status_code == 404


def test_transcript_routes_require_authentication_and_origin(client, make_user, login_as):
    assert client.post("/api/v1/transcripts").status_code == 401
    login_as(make_user())
    assert upload(client, {"Origin": "https://evil.invalid"}, pdf(TRANSCRIPT)).status_code == 403


def test_logs_never_contain_uploaded_content_and_file_names_are_sanitized(client, make_user, login_as, post_headers, caplog):
    from app.extensions import db
    from app.models import Transcript

    caplog.set_level(logging.DEBUG)
    login_as(make_user())
    before = {path.name for path in Path(tempfile.gettempdir()).iterdir()}
    name = "../../" + "x" * 300 + ".pdf"
    identity = upload(client, post_headers, pdf(TRANSCRIPT), name=name).json["id"]
    assert not any(MARKER in record.getMessage() or "CSCI 1133" in record.getMessage() for record in caplog.records)
    stored = db.session.get(Transcript, identity).file_name
    assert "/" not in stored and "\\" not in stored and ".." not in stored and len(stored) <= 255
    created = {path for path in Path(tempfile.gettempdir()).iterdir() if path.name not in before and path.is_file()}
    assert not any(MARKER.encode() in path.read_bytes() for path in created if path.stat().st_size < 50_000_000)


def test_database_session_is_not_held_while_parsing(client, make_user, login_as, post_headers, monkeypatch):
    from app.extensions import db
    from app.services import transcripts

    states = []
    original = transcripts.extract_pdf_text

    def observe(data):
        states.append(db.session().in_transaction())
        return original(data)

    monkeypatch.setattr(transcripts, "extract_pdf_text", observe)
    login_as(make_user())
    assert upload(client, post_headers, pdf(TRANSCRIPT)).status_code == 201
    assert states == [False]


def test_unexpected_parser_errors_mark_the_transcript_failed_instead_of_parsing_forever(client, make_user, login_as, post_headers, monkeypatch):
    from app.services import transcripts

    def explode(text):
        raise RuntimeError("synthetic parser failure")

    monkeypatch.setattr(transcripts, "parse_transcript_text", explode)
    login_as(make_user())
    response = upload(client, post_headers, pdf(TRANSCRIPT))
    assert response.status_code == 201
    body = client.get(f"/api/v1/transcripts/{response.json['id']}").json
    assert (body["status"], body["errorCode"]) == ("failed", "parse_error")


def scanned_pdf(lines, *, messy=False):
    """An image-only PDF (no text layer), optionally skewed, blurred and speckled like a bad scan."""
    import random

    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    image = Image.new("L", (1700, 1100), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=34)
    for index, line in enumerate(lines):
        draw.text((80, 80 + index * 70), line, fill=0, font=font)
    if messy:
        noise = random.Random(7)
        for _ in range(4000):
            draw.point((noise.randrange(1700), noise.randrange(1100)), fill=noise.randrange(90, 200))
        image = image.rotate(1.5, expand=True, fillcolor=255).filter(ImageFilter.GaussianBlur(0.8))
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(image.width / 2, image.height / 2))
    page.drawImage(ImageReader(image.convert("RGB")), 0, 0, image.width / 2, image.height / 2)
    page.showPage()
    page.save()
    return buffer.getvalue()


@pytest.mark.parametrize("messy", [False, True])
def test_scanned_pdf_is_read_with_ocr_without_logging_its_text(client, make_user, login_as, post_headers, caplog, messy):
    from app.parsers.pdf_text import extract_pdf_text

    data = scanned_pdf(TRANSCRIPT, messy=messy)
    assert extract_pdf_text(data).strip() == ""  # really image-only
    caplog.set_level(logging.DEBUG)
    login_as(make_user())
    identity = upload(client, post_headers, data).json["id"]
    transcript = client.get(f"/api/v1/transcripts/{identity}").json
    assert transcript["status"] == "parsed"
    assert {course["code"] for course in transcript["courses"]} == {"CSCI 1133", "MATH 1271", "CSCI 1933"}
    assert {course["term"] for course in transcript["courses"]} == {"Fall 2025", "Spring 2026"}
    assert not any(MARKER in record.getMessage() or "CSCI 1133" in record.getMessage() for record in caplog.records)


def test_ocr_lines_are_rebuilt_top_to_bottom_and_left_to_right():
    from app.parsers.ocr import lines_from_boxes

    def box(x, y, width=100, height=20):
        return [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]

    boxes = [box(400, 102), box(10, 100), box(10, 160), box(200, 98)]
    texts = ["4.0 A-", "CSCI 1133", "Fall 2025", "Intro"]
    assert lines_from_boxes(boxes, texts) == ["CSCI 1133 Intro 4.0 A-", "Fall 2025"]


def test_ocr_reads_at_most_the_page_limit(monkeypatch):
    from app.parsers import ocr

    seen = []
    monkeypatch.setattr(ocr, "recognize_page", lambda image: seen.append(image) or [])
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    for _ in range(ocr.MAX_PAGES + 3):
        page.showPage()
    page.save()
    ocr.ocr_pdf_text(buffer.getvalue())
    assert len(seen) == ocr.MAX_PAGES


@pytest.mark.parametrize("raw, fixed", [
    ("CSCI 1133Introduction to Computing 4.0A-", "CSCI 1133 Introduction to Computing 4.0 A-"),
    ("MATH 1271 CalculusI4.0 B", "MATH 1271 CalculusI 4.0 B"),
    ("CSCI 1933Data Structures4.0 IP", "CSCI 1933 Data Structures 4.0 IP"),
    ("CSCI 1133H Honors Intro 4.0 A", "CSCI 1133H Honors Intro 4.0 A"),
    ("Fall 2025", "Fall 2025"),
])
def test_ocr_spacing_is_restored_at_row_boundaries(raw, fixed):
    from app.parsers.ocr import restore_spacing
    assert restore_spacing(raw) == fixed


APAS_LINES = [f"{MARKER} Synthetic Audit", "Term Course Credit Grade Title",
              "F 25 1CSCI1133 4.0 A SYNTHETIC PROGRAMMING", "SP26 1MATH1272 4.0 B+",
              "F 26 1CSCI2041 4.0 AF IP Synthetic Principles", "SP27 1CSCI4041 4.0 AF FT Synthetic Algorithms",
              "SI26 1HUM 1T001 3.0 IP SYNTHETIC PLACEHOLDER", "SP24 1CSCI1103 0.0 N2 SYNTHETIC EXAM"]


def test_apas_audit_imports_courses_and_reports_what_was_not_imported(client, make_user, login_as, post_headers):
    login_as(make_user())
    identity = upload(client, post_headers, pdf(APAS_LINES)).json["id"]
    transcript = client.get(f"/api/v1/transcripts/{identity}").json
    assert (transcript["status"], transcript["completed"], transcript["inProgress"]) == ("parsed", 2, 2)
    assert {(c["code"], c["term"]) for c in transcript["courses"]} == {
        ("CSCI 1133", "Fall 2025"), ("MATH 1272", "Spring 2026"), ("CSCI 2041", "Fall 2026"), ("CSCI 4041", "Spring 2027")}
    assert transcript["notImported"] == ["HUM 1T001"]


def test_unreadable_text_layer_falls_back_to_ocr(client, make_user, login_as, post_headers, monkeypatch):
    from app.services import transcripts

    monkeypatch.setattr(transcripts, "ocr_pdf_text", lambda data: "\n".join(APAS_LINES))
    login_as(make_user())
    identity = upload(client, post_headers, pdf(["Th1s lay3r is g@rbled", "n0 r0ws here"])).json["id"]
    transcript = client.get(f"/api/v1/transcripts/{identity}").json
    assert (transcript["status"], transcript["completed"]) == ("parsed", 2)


def test_parsed_upload_without_skipped_codes_reports_an_empty_list(client, make_user, login_as, post_headers):
    login_as(make_user())
    identity = upload(client, post_headers, pdf(TRANSCRIPT)).json["id"]
    assert client.get(f"/api/v1/transcripts/{identity}").json["notImported"] == []


def test_misread_text_layer_is_replaced_by_a_better_ocr_read(client, make_user, login_as, post_headers, monkeypatch):
    from app.services import transcripts

    calls = []
    monkeypatch.setattr(transcripts, "ocr_pdf_text", lambda data: calls.append(1) or "\n".join(APAS_LINES))
    login_as(make_user())
    garbled = ["F 25 1CSCI133 4.0 A DROPPED DIGIT", "SP26 1MATH1272 4.0 B+"]
    identity = upload(client, post_headers, pdf(garbled)).json["id"]
    transcript = client.get(f"/api/v1/transcripts/{identity}").json
    assert calls and transcript["completed"] == 2 and transcript["notImported"] == ["HUM 1T001"]


def test_clean_text_layer_with_only_placeholders_skips_ocr(client, make_user, login_as, post_headers, monkeypatch):
    from app.services import transcripts

    monkeypatch.setattr(transcripts, "ocr_pdf_text", lambda data: pytest.fail("OCR should not run"))
    login_as(make_user())
    identity = upload(client, post_headers, pdf(APAS_LINES)).json["id"]
    assert client.get(f"/api/v1/transcripts/{identity}").json["notImported"] == ["HUM 1T001"]


def test_unknown_subject_in_text_layer_triggers_ocr(client, catalog, make_user, login_as, post_headers, monkeypatch):
    from app.services import transcripts

    calls = []
    monkeypatch.setattr(transcripts, "ocr_pdf_text", lambda data: calls.append(1) or "")
    login_as(make_user())
    upload(client, post_headers, pdf(["SP26 1CSCI1001 4.0 A FINE", "SP26 1QQQQ1000 4.0 A UNKNOWN"]))
    assert calls


def huge_page_pdf(width_pt, height_pt, pages=1):
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=(width_pt, height_pt))
    for _ in range(pages):
        page.showPage()
    page.save()
    return buffer.getvalue()


def test_ocr_scales_oversized_pages_down_to_the_pixel_budget(monkeypatch):
    from app.parsers import ocr

    seen = []
    monkeypatch.setattr(ocr, "recognize_page", lambda image: seen.append(image.size) or [])
    ocr.ocr_pdf_text(huge_page_pdf(14000, 14000))  # about 194 inches square
    assert seen and seen[0][0] * seen[0][1] <= ocr.MAX_PAGE_PIXELS


def test_ocr_stops_at_the_total_pixel_budget(monkeypatch):
    from app.parsers import ocr

    seen = []
    monkeypatch.setattr(ocr, "recognize_page", lambda image: seen.append(image.size) or [])
    monkeypatch.setattr(ocr, "MAX_TOTAL_PIXELS", ocr.MAX_PAGE_PIXELS * 2)
    ocr.ocr_pdf_text(huge_page_pdf(14000, 14000, pages=5))
    assert len(seen) == 2


def test_text_extraction_reads_at_most_the_page_limit_and_caps_text(monkeypatch):
    from app.parsers import pdf_text

    many = pdf(["CSCI 1133  Intro  4.0  A"] * 3)
    assert "CSCI 1133" in pdf_text.extract_pdf_text(many)
    monkeypatch.setattr(pdf_text, "MAX_CHARS", 10)
    assert len(pdf_text.extract_pdf_text(many)) <= 10
    from reportlab.pdfgen import canvas
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    for index in range(pdf_text.MAX_PAGES + 5):
        page.drawString(40, 800, f"PAGE{index:03d}")
        page.showPage()
    page.save()
    monkeypatch.setattr(pdf_text, "MAX_CHARS", 10**6)
    text = pdf_text.extract_pdf_text(buffer.getvalue())
    assert f"PAGE{pdf_text.MAX_PAGES - 1:03d}" in text and f"PAGE{pdf_text.MAX_PAGES:03d}" not in text
