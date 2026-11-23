"""Transcript text parsers: APAS degree audits (parse_apas_text) and a generic one-row-per-course layout.

The APAS row layout was checked against real Twin Cities audits (2026-11-23), both scanned and with
third-party OCR text layers; tests use synthetic rows only. Generic format, one item per line:

    Fall 2025                                   term header
    CSCI 1133  Introduction to Computing  4.0  A-   course row: code, title, credits, grade
    WRIT 1301  University Writing          3.0  IP   IP means in progress

Rows before any term header have an unknown term. Other lines (page headers, names) are ignored.
"""
import re

TERM = re.compile(r"^(Fall|Spring|Summer) ([1-9]\d{3})$")
ROW = re.compile(r"^(?P<code>[A-Z]{2,6} \d{4}[A-Z]?)\s+(?P<title>\S.*?)\s+(?P<credits>\d{1,2}(?:\.\d)?)\s+"
                 r"(?P<grade>A-?|B[+-]?|C[+-]?|D\+?|F|S|N|W|I|IP)$")
MAX_LINES = 5000

# APAS audit rows, e.g. "SP25 1CSCI1133 4.0 A Title" or "F 26 1SW 2501W 4.0 AF IP Title". The leading
# "1" is the campus prefix. Tolerates noise from third-party OCR text layers: lowercase l for I,
# dropped decimal points ("40" for 4.0), fused grade tokens ("AFIP", "1P"), titles on their own line.
APAS_ROW = re.compile(r"^(?P<season>F|SP|S[IlU1|]|SU)\s?(?P<year>\d{2})\s+1\s?(?P<subject>[A-Za-z]{2,6})\s?"
                      r"(?P<number>[0-9A-Za-z]{3,6})\s+(?P<credits>\d{1,2}(?:\.\d)?)(?:\s+(?P<rest>.*))?$")
APAS_SEASONS = {"F": "Fall", "SP": "Spring"}  # every S-prefixed code other than SP is a summer session
COURSE_NUMBER = re.compile(r"^\d{4}[A-Z]?$")
PASSING = {"A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "S"}
FAILED = re.compile(r"^(?:N\d?|F|W|I)$")
TRANSFER = re.compile(r"^T\d?$")


def _apas_grade(rest):
    """Return (status, grade, title) or None for a failed or withdrawn attempt."""
    tokens = re.sub(r"\bAF(IP|FT)\b", r"AF \1", rest or "").split()
    if tokens and tokens[0] == "AF":
        tokens = tokens[1:]
    if not tokens:
        return "done", None, ""
    head = {"1P": "IP"}.get(tokens[0], tokens[0])
    title = " ".join(tokens[1:])
    if head in {"IP", "FT"}:
        return "prog", None, title
    if TRANSFER.match(head):
        return "done", None, title
    if head in PASSING:
        return "done", head, title
    if FAILED.match(head):
        return None
    return "done", None, " ".join(tokens)


def _resolve(subject, number, known_codes):
    """Return the course code to import, or None when it cannot be trusted.

    Without ``known_codes`` every well-formed code is accepted. With it, codes under an unknown subject
    are repaired only for OCR misreads seen in real scans ("I" read as "H", or "I4" fused into "H"), and
    only when the repaired code exists in the catalog. Unrepairable codes are never guessed."""
    if not COURSE_NUMBER.match(number) and not (known_codes and re.fullmatch(r"\d{3}[A-Z]?", number)):
        return None
    code = f"{subject} {number}"
    if known_codes is None:
        return code if COURSE_NUMBER.match(number) else None
    subjects = {known.split(" ")[0] for known in known_codes}
    if subject in subjects:
        return code if COURSE_NUMBER.match(number) else None
    if subject.endswith("H"):
        for candidate in (f"{subject[:-1]}I {number}", f"{subject[:-1]}I 4{number}"):
            if candidate in known_codes:
                return candidate
    return None


def parse_apas_text(text, *, known_codes=None):
    """Return (rows, skipped codes). Failed attempts are dropped silently; placeholder and unreadable
    codes are reported so the student can add them by hand. Never raises."""
    try:
        if known_codes is not None:
            known_codes = frozenset(known_codes)
        if not isinstance(text, str):
            return [], []
        rows, seen, skipped = [], set(), set()
        for raw in text.splitlines()[:MAX_LINES]:
            line = re.sub(r"\s+", " ", raw).strip()
            match = APAS_ROW.match(line) if len(line) <= 400 else None
            if not match:
                continue
            subject = match.group("subject").replace("l", "I").upper()
            number = match.group("number").upper()
            credits_text = match.group("credits")
            credits = float(credits_text) if "." in credits_text else int(credits_text) / (10 if len(credits_text) == 2 else 1)
            parsed = _apas_grade(match.group("rest"))
            if parsed is None:
                continue
            raw_code = f"{subject} {number}"
            code = None if subject == "NOTR" else _resolve(subject, number, known_codes)
            if code is None or not 0 < credits <= 12 or (credits * 2) % 1:
                skipped.add(raw_code)
                continue
            season = APAS_SEASONS.get(match.group("season"), "Summer")
            term = f"{season} 20{match.group('year')}"
            if (code, term) in seen:
                continue
            seen.add((code, term))
            status, grade, title = parsed
            rows.append({"code": code, "title": title.strip()[:255] or code, "credits": credits,
                         "grade": grade, "term": term, "status": status})
        return rows, sorted(skipped)
    except Exception:  # noqa: BLE001 - garbage input must never raise
        return [], []


def parse_transcript_text(text):
    """Return parsed rows; unrecognized input yields []. Never raises."""
    try:
        if not isinstance(text, str):
            return []
        rows, term = [], None
        for raw in text.splitlines()[:MAX_LINES]:
            line = re.sub(r"\s+", " ", raw).strip()
            if len(line) > 400:
                continue
            header = TERM.match(line)
            if header:
                term = line
                continue
            match = ROW.match(line)
            if not match:
                continue
            credits = float(match.group("credits"))
            title = match.group("title").strip()
            if not 0 < credits <= 12 or (credits * 2) % 1 or not 1 <= len(title) <= 255:
                continue
            grade = match.group("grade")
            in_progress = grade == "IP"
            rows.append({"code": match.group("code"), "title": title, "credits": credits,
                         "grade": None if in_progress else grade, "term": term, "status": "prog" if in_progress else "done"})
        return rows
    except Exception:  # noqa: BLE001 - garbage input must never raise
        return []
