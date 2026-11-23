"""Provisional synthetic transcript text format. No real transcript or APAS sample has been provided."""
import pytest

SAMPLE = """University of Minnesota Synthetic Record
Page 1 of 2

Fall 2025
CSCI 1133  Introduction to Computing   4.0  A-
MATH 1271  Calculus I                  4    B+

Spring 2026
CSCI 1933H Honors Data Structures      4.0  S
WRIT 1301  University Writing          3.0  IP
Page 2 of 2
"""


def parse(text):
    from app.parsers.transcript import parse_transcript_text
    return parse_transcript_text(text)


def test_parser_extracts_code_title_credits_grade_term_and_status():
    assert parse(SAMPLE) == [
        {"code": "CSCI 1133", "title": "Introduction to Computing", "credits": 4.0, "grade": "A-", "term": "Fall 2025", "status": "done"},
        {"code": "MATH 1271", "title": "Calculus I", "credits": 4.0, "grade": "B+", "term": "Fall 2025", "status": "done"},
        {"code": "CSCI 1933H", "title": "Honors Data Structures", "credits": 4.0, "grade": "S", "term": "Spring 2026", "status": "done"},
        {"code": "WRIT 1301", "title": "University Writing", "credits": 3.0, "grade": None, "term": "Spring 2026", "status": "prog"},
    ]


def test_rows_before_any_term_header_have_an_unknown_term():
    assert parse("CSCI 1133  Introduction to Computing  4.0  A")[0]["term"] is None


@pytest.mark.parametrize("text", ["", "Nothing recognizable here", "CSCI 1133 Intro 13.0 A", "CSCI 1133 Intro 0.3 A",
                                  "CSCI 1133 Intro 4.0 Z", "csci 1133 Intro 4.0 A"])
def test_unrecognized_or_invalid_rows_are_skipped(text):
    assert parse(text) == []


@pytest.mark.parametrize("garbage", [None, 5, b"%PDF", {"text": 1}, "\x00\x01\x02" * 50, "A" * 100000],
                         ids=["none", "number", "bytes", "dict", "control", "long"])
def test_parser_never_raises_on_garbage(garbage):
    assert parse(garbage) == []


# APAS audit rows: "<term> 1<SUBJ><NUM> <credits> [AF] <grade> [title]". Synthetic rows, with the
# noise third-party OCR text layers add (l for I, dropped decimal points, fused tokens, split titles).
APAS = """Term Course Credit Grade Title
SP23 1HIST1999 3.0 T4 SYNTHETIC HISTORY
F 25 1CSCl1133 7.0 A
SP25 1POL 1001 3.0 A Synthetic Politics
SP26 1 MATH1272 50 B SYNTHETIC CALCULUS II
SI26 1CSCI1933 4.0 B+ SYNTHETIC STRUCTURES
F 26 1CSCI2033 4.0 AF IP Synthetic Linear Algebra
F26 1SW 2501W 40 AFIP Synthetic Justice
SP27 1CSCl4041 40 AF FT Synthetic Algorithms
SP24 1CSCI1103 0.0 N2 SYNTHETIC AP EXAM
SP24 1CSCI1104 4.0 W Synthetic Withdrawn
SI26 1HUM 1T001 3.0 IP SYNTHETIC PLACEHOLDER
SP24 1NOTR0T002 1.0 T3 SYNTHETIC NON TRANSFER
SP27 1CSCH521 30 AF FT Garbled Code
F 26 1CSCI2033 4.0 AF IP Synthetic Linear Algebra
"""


def apas(text):
    from app.parsers.transcript import parse_apas_text
    return parse_apas_text(text)


def test_apas_rows_map_terms_grades_and_statuses():
    rows, _ = apas(APAS)
    assert [(r["code"], r["term"], r["credits"], r["grade"], r["status"]) for r in rows] == [
        ("HIST 1999", "Spring 2023", 3.0, None, "done"),
        ("CSCI 1133", "Fall 2025", 7.0, "A", "done"),
        ("POL 1001", "Spring 2025", 3.0, "A", "done"),
        ("MATH 1272", "Spring 2026", 5.0, "B", "done"),
        ("CSCI 1933", "Summer 2026", 4.0, "B+", "done"),
        ("CSCI 2033", "Fall 2026", 4.0, None, "prog"),
        ("SW 2501W", "Fall 2026", 4.0, None, "prog"),
        ("CSCI 4041", "Spring 2027", 4.0, None, "prog"),
    ]


def test_apas_titles_come_from_the_row_or_fall_back_to_the_code():
    rows, _ = apas(APAS)
    titles = {r["code"]: r["title"] for r in rows}
    assert titles["POL 1001"] == "Synthetic Politics"
    assert titles["CSCI 1133"] == "CSCI 1133"


def test_apas_reports_placeholders_and_unreadable_codes_but_not_failed_attempts():
    _, skipped = apas(APAS)
    assert skipped == ["CSCH 521", "HUM 1T001", "NOTR 0T002"]


@pytest.mark.parametrize("garbage", [None, 5, "", "SP25 1CSCI1133", "\x00" * 99, "SP25 " * 20000],
                         ids=["none", "number", "empty", "no-credits", "control", "long"])
def test_apas_parser_never_raises(garbage):
    assert apas(garbage) == ([], [])


KNOWN = {"CSCI 4041", "CSCI 4707", "CSCI 1133", "MATH 1272"}


def test_known_codes_repair_ocr_misreads_only_when_the_repair_exists():
    from app.parsers.transcript import parse_apas_text

    rows, skipped = parse_apas_text(
        "SP27 1CSCH041 40 AF FT Garbled Fused\n"      # "I4" read as "H": CSCI 4041
        "SP26 1CSCH4707 40 A Garbled Letter\n"        # "I" read as "H": CSCI 4707
        "SP26 1CSCH4708 40 A No Such Course\n"        # repair does not exist: not imported
        "F 25 1CSCI133 70 A Dropped Digit\n"          # unrecoverable
        "SP26 1MATH1272 50 B Fine\n"
        "SP26 1QQQQ1000 40 A Unknown Subject\n",
        known_codes=KNOWN)
    assert [(r["code"], r["term"]) for r in rows] == [
        ("CSCI 4041", "Spring 2027"), ("CSCI 4707", "Spring 2026"), ("MATH 1272", "Spring 2026")]
    assert skipped == ["CSCH 4708", "CSCI 133", "QQQQ 1000"]


def test_repaired_rows_do_not_duplicate_a_cleanly_read_row():
    from app.parsers.transcript import parse_apas_text

    rows, _ = parse_apas_text("SP27 1CSCl4041 4.0 AF FT A\nSP27 1CSCH041 40 AF FT A", known_codes=KNOWN)
    assert [r["code"] for r in rows] == ["CSCI 4041"]


LE_AUDIT = """Liberal Education Requirements
First-Year Writing
F 25 1WRIT1301 4.0 A SYNTHETIC WRITING
Writing Intensive
Transfer Courses That Do Not Count as Writing Intensive
F 25 1PHYS1301W 4.0 B SYNTHETIC PHYSICS
Diversified Core -Historical Perspectives & Social
Sciences
Historical Perspectives
1) 1 course taken
SP23 1HIST1999 3.0 T4 SYNTHETIC HISTORY
m Social Sciences
2) 0 courses taken
II Arts/Humanities
In prog: 1 course taken
SP26 1ARTS1001 3.0 IP SYNTHETIC ART
m Literature
Diversified Core -Mathematical Thinking
m Mathematical Thinking
F 25 1MATH1271 4.0 A SYNTHETIC CALCULUS
Designated Themes
1 Race, Power, and Justice in the United States
II The Environment
SP27 1ESCI1003 4.0 AF FT SYNTHETIC EARTH
Computer Science BSCompSci - Major Requirements
F 25 1CSCI1133 4.0 A NOT LIBERAL EDUCATION
"""


def test_apas_liberal_education_section_reports_required_and_covered_categories():
    from app.parsers.transcript import parse_apas_le
    required, covered = parse_apas_le(LE_AUDIT)
    assert required == {"Historical Perspectives", "Social Sciences", "Arts/Humanities", "Literature",
                        "Mathematical Thinking", "Race, Power, and Justice US", "Environment"}
    assert covered == {"Historical Perspectives", "Arts/Humanities", "Mathematical Thinking", "Environment"}


@pytest.mark.parametrize("text", [None, "", "Major Requirements only", "Liberal Education Requirements\nnothing"],
                         ids=["none", "empty", "no-section", "no-categories"])
def test_apas_liberal_education_parse_returns_none_when_absent(text):
    from app.parsers.transcript import parse_apas_le
    assert parse_apas_le(text) is None


def test_prose_mentioning_major_requirements_does_not_end_the_section():
    from app.parsers.transcript import parse_apas_le
    text = LE_AUDIT.replace("Writing Intensive\n", "Writing Intensive\nwithin the core major requirements, students must choose\n", 1)
    assert parse_apas_le(text) == parse_apas_le(LE_AUDIT)
