"""Sample plan exporter parsing. Synthetic HTML shaped like sampleplan.umn.edu; no network."""
INDEX = """<html><body><table>
<tr><td>College A</td><td><a href="/twin-cities/synthetic-studies-ba">Synthetic Studies BA</a></td></tr>
<tr><td>College B</td><td><a href="/twin-cities/other-bs">Other BS</a></td></tr>
<tr><td><a href="https://docs.google.com/spreadsheets/d/x">Printable</a></td></tr>
<tr><td><a href="/twin-cities/synthetic-studies-ba">duplicate</a></td></tr>
</table></body></html>"""

PAGE = """<html><body><h1><span>Synthetic Studies B.A.</span></h1>
<div class="accordion">
<h3><span class="arrow">+</span><div>Synthetic Studies BA</div></h3>
<div class="interior">
<h4>Year 1: Fall Semester</h4>
<table><thead><tr><th>Course</th><th>Title</th><th>Credits</th><th>LE</th></tr></thead><tbody>
<tr><td>SYN 1001</td><td>Intro Synthetic (Preferred Course)</td><td>4</td><td>Mth</td></tr>
<tr><td colspan="2">SYN 1002</td><td>1</td><td>&nbsp;</td></tr>
<tr><td>LE</td><td>Arts/Humanities, Race, Power, and Justice US</td><td>3</td><td>AH, RPJ</td></tr>
<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
<tr><td>&nbsp;</td><td><em>Term credits</em></td><td>8</td><td>&nbsp;</td></tr>
</tbody></table>
<h4>Year 1: Spring Semester</h4>
<table><tbody>
<tr><td>Elective </td><td>&nbsp;</td><td>3</td><td></td></tr>
<tr><td>SYN 2001 or SYN 2002</td><td>Choice</td><td>3-4</td><td></td></tr>
</tbody></table>
</div>
<h3><span class="arrow">+</span><div>Integrated Synthetic B.A./M.A.</div></h3>
<div class="interior"><h4>Year 1: Fall Semester</h4>
<table><tbody><tr><td>SYN 1001</td><td>Intro</td><td>4</td><td></td></tr></tbody></table></div>
</div></body></html>"""


def test_index_lists_unique_twin_cities_plan_pages_only():
    from scripts.export_sample_plans import plan_links
    assert plan_links(INDEX) == ["/twin-cities/other-bs", "/twin-cities/synthetic-studies-ba"]


def test_plan_page_rows_keep_terms_courses_le_slots_and_electives():
    from scripts.export_sample_plans import parse_plan_page
    rows = parse_plan_page(PAGE, url="https://sampleplan.umn.edu/twin-cities/synthetic-studies-ba")
    first = [row for row in rows if row["plan"] == "Synthetic Studies BA"]
    assert [(r["year"], r["season"], r["kind"], r["code"], r["credits"], r["le"], r["preferred"]) for r in first] == [
        (1, "Fall", "course", "SYN 1001", "4", "Mth", "true"),
        (1, "Fall", "course", "SYN 1002", "1", "", "false"),
        (1, "Fall", "le", "", "3", "AH, RPJ", "false"),
        (1, "Spring", "elective", "", "3", "", "false"),
        (1, "Spring", "choice", "SYN 2001 or SYN 2002", "3-4", "", "false"),
    ]
    assert first[0]["title"] == "Intro Synthetic"
    assert first[2]["title"] == "Arts/Humanities, Race, Power, and Justice US"
    assert {r["program_title"] for r in rows} == {"Synthetic Studies B.A."}
    assert [r["plan"] for r in rows].count("Integrated Synthetic B.A./M.A.") == 1


def test_garbage_pages_yield_no_rows():
    from scripts.export_sample_plans import parse_plan_page
    assert parse_plan_page("<html>nothing</html>", url="x") == []


def test_paragraph_term_headers_blank_plan_headers_and_merged_course_titles():
    from scripts.export_sample_plans import parse_plan_page
    page = '''<h1>Synthetic studies</h1><h2 class="accordion-title">Synthetic calculus track</h2>
    <h3><span aria-hidden="true" class="arrow">+</span></h3>
    <p><strong>Year 1: Fall Semester</strong></p><table>
    <tr><td>Course</td><td>Title</td><td>Credits</td><td>LE</td></tr>
    <tr><td colspan="2">SYN 1001 Synthetic intro</td><td>4</td><td></td></tr></table>
    <p><strong>Year 1: Spring Semester</strong></p><table>
    <tr><td>LE</td><td>Synthetic perspective</td><td>3</td><td>SP</td></tr></table>'''
    rows = parse_plan_page(page, url="https://example.invalid/synthetic")
    assert [(r["plan"], r["season"], r["kind"], r["code"], r["title"]) for r in rows] == [
        ("Synthetic calculus track", "Fall", "course", "SYN 1001", "Synthetic intro"),
        ("Synthetic calculus track", "Spring", "le", "", "Synthetic perspective")]


def test_offered_column_is_not_misread_as_credits():
    from scripts.export_sample_plans import parse_plan_page
    page = '''<h1>Synthetic</h1><h3>Synthetic plan</h3><h4>Year 1: Fall Semester</h4><table>
    <tr><td>SYN 1001*</td><td>Synthetic intro</td><td>Fall/Spring</td><td>4</td><td>SP</td></tr>
    <tr><td>LE*</td><td>Synthetic perspective</td><td>Fall</td><td>3</td><td>SP</td></tr></table>'''
    rows = parse_plan_page(page, url="https://example.invalid")
    assert [(r["kind"], r["code"], r["credits"]) for r in rows] == [("course", "SYN 1001", "4"), ("le", "", "3")]


def test_export_retries_rate_limits_and_reuses_public_source_cache(tmp_path, monkeypatch):
    import csv
    import requests
    from scripts import export_sample_plans as exporter
    class Response:
        def __init__(self, text, status=200):
            self.text, self.status_code, self.headers = text, status, {"Retry-After": "1"}
            self.ok = status == 200
        def raise_for_status(self):
            assert self.ok
    index = '<a href="/twin-cities/synthetic-studies-ba">Synthetic</a>'
    responses = iter([Response(index), Response("", 429), Response(PAGE), Response(index)])
    class Session:
        headers = {}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, *args, **kwargs):
            return next(responses)
    monkeypatch.setattr(requests, "Session", Session)
    sleeps = []
    monkeypatch.setattr(exporter.time, "sleep", sleeps.append)
    output, cache = tmp_path / "synthetic.csv", tmp_path / "source"
    args = ["--output", str(output), "--source-cache", str(cache)]
    exporter.main(args)
    assert 30 in sleeps
    first = list(csv.DictReader(output.open(encoding="utf-8")))
    assert len(first) == 6
    exporter.main(args)
    assert len(list(csv.DictReader(output.open(encoding="utf-8")))) == len(first)
