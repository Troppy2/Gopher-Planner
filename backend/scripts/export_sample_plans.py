"""Export public UMN Twin Cities four-year sample plans (sampleplan.umn.edu) to a dated CSV.

Run from `backend`:

    uv run python scripts/export_sample_plans.py --output data/catalog-exports/sample-plans.<date>.csv

Only `/twin-cities/<slug>` pages are fetched (allowed by the site's robots.txt), one request per
second. Rows are kept as published: course rows, LE (liberal education) slots, electives, and
"A or B" choices. Source evidence only; the app reads the CSV through the program builder.
"""
import argparse
import csv
import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

BASE = "https://sampleplan.umn.edu"
INDEX = f"{BASE}/tc-sample-plans"
FIELDS = ["url", "program_title", "plan", "year", "season", "kind", "code", "title", "credits", "le", "preferred",
          "retrieved_at_utc"]
LINK = re.compile(r'href="(/twin-cities/[a-z0-9-]+)"')
CODE = re.compile(r"^[A-Z]{2,6} \d{4}[A-Z]?$")
TERM = re.compile(r"Year\s+(\d)\s*:\s*(Fall|Spring|Summer)", re.IGNORECASE)
PLAN_HEADER = re.compile(r"<h3[^>]*>(.*?)</h3>", re.IGNORECASE | re.DOTALL)
TERM_HEADER = re.compile(r"<(?:h4|p)\b[^>]*>(.*?)</(?:h4|p)>", re.IGNORECASE | re.DOTALL)
SECTION_HEADER = re.compile(r'<h2\b[^>]*class="[^"]*accordion-title[^"]*"[^>]*>(.*?)</h2>', re.IGNORECASE | re.DOTALL)
ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
TITLE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
PREFERRED = re.compile(r"\s*\(Preferred Course\)\s*", re.IGNORECASE)


def text(html):
    value = unescape(re.sub(r"<[^>]+>", " ", html or "")).replace("\xa0", " ").replace("\u2014", " - ")
    return re.sub(r"\s+", " ", value).strip()


def plan_links(html):
    return sorted(set(LINK.findall(html or "")))


def _row(cells):
    """Return (kind, code, title, credits, le, preferred) or None for blank and total rows."""
    if len(cells) == 5:  # some plans insert an Offered column before Credits
        cells = [*cells[:2], *cells[3:]]
    if len(cells) == 3:  # a colspan cell merged course and title
        cells = [cells[0], "", cells[1], cells[2]]
    if len(cells) < 3:
        return None
    first, title, credits = cells[0].rstrip("* "), cells[1], cells[2]
    le = cells[3] if len(cells) > 3 else ""
    if not re.search(r"\d", credits) or "term credits" in title.lower() or "total" in first.lower():
        return None
    preferred = bool(PREFERRED.search(title))
    title = PREFERRED.sub(" ", title).strip()
    merged = re.fullmatch(r"([A-Z]{2,6} \d{4}[A-Z]?)\s+(.+)", first) if not title else None
    if merged and not re.search(r"\bor\b", merged.group(2), re.IGNORECASE):
        return "course", merged.group(1), merged.group(2), credits, le, preferred
    if CODE.match(first):
        return "course", first, title, credits, le, preferred
    if first.upper() == "LE":
        return "le", "", title, credits, le, preferred
    if first.lower().startswith("elective") or title.lower().startswith("elective"):
        return "elective", "", title, credits, le, preferred
    if re.search(r"[A-Z]{2,6} \d{4}", first):
        return "choice", first, title, credits, le, preferred
    if first or title:
        return "other", "", " ".join(part for part in (first, title) if part), credits, le, preferred
    return None


def parse_plan_page(html, *, url, retrieved_at=""):
    """Rows for every plan on one page. Unrecognized pages yield []."""
    html = html or ""
    title = TITLE.search(html)
    program_title = text(title.group(1)) if title else ""
    headers = list(PLAN_HEADER.finditer(html))
    rows = []
    for index, header in enumerate(headers):
        plan = text(re.sub(r'<span\b[^>]*class="arrow"[^>]*>.*?</span>', "", header.group(1)))
        if not plan:
            preceding = list(SECTION_HEADER.finditer(html[:header.start()]))
            plan = text(preceding[-1].group(1)) if preceding else program_title
        body = html[header.end(): headers[index + 1].start() if index + 1 < len(headers) else len(html)]
        terms = [term for term in TERM_HEADER.finditer(body) if TERM.search(text(term.group(1)))]
        for position, term in enumerate(terms):
            match = TERM.search(text(term.group(1)))
            if not match:
                continue
            year, season = int(match.group(1)), match.group(2).capitalize()
            chunk = body[term.end(): terms[position + 1].start() if position + 1 < len(terms) else len(body)]
            for raw in ROW.findall(chunk):
                parsed = _row([text(cell) for cell in CELL.findall(raw)])
                if parsed is None:
                    continue
                kind, code, row_title, credits, le, preferred = parsed
                rows.append({"url": url, "program_title": program_title, "plan": plan, "year": year, "season": season,
                             "kind": kind, "code": code, "title": row_title, "credits": credits, "le": le,
                             "preferred": "true" if preferred else "false", "retrieved_at_utc": retrieved_at})
    return rows


def main(argv=None):
    import requests

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--source-cache", type=Path, help="Local public HTML cache for repeatable exports")
    args = parser.parse_args(argv)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    rows, failures = [], []
    with requests.Session() as session:
        session.headers["User-Agent"] = "GopherPlanner-sample-plan-export"
        links = plan_links(session.get(INDEX, timeout=30).text)
        for link in links:
            cached = args.source_cache / f"{link.rsplit('/', 1)[-1]}.html" if args.source_cache else None
            page_rows = parse_plan_page(cached.read_text(encoding="utf-8"), url=BASE + link, retrieved_at=retrieved_at) if cached and cached.is_file() else []
            for attempt in range(3 if not page_rows else 0):
                time.sleep(max(args.delay, 2 ** attempt if attempt else args.delay))
                response = session.get(BASE + link, timeout=30)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "30")
                    time.sleep(max(30, min(60, int(retry_after))) if retry_after.isdigit() else 30)
                if response.ok:
                    page_rows = parse_plan_page(response.text, url=BASE + link, retrieved_at=retrieved_at)
                    if page_rows:
                        if cached:
                            cached.parent.mkdir(parents=True, exist_ok=True)
                            cached.write_text(response.text, encoding="utf-8")
                        break
                if attempt == 2:
                    response.raise_for_status()
            if not page_rows:
                failures.append(link)
            rows.extend(page_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(links)} pages, {len(rows)} rows, {len(failures)} pages without a plan: {', '.join(failures)}")


if __name__ == "__main__":
    main()
