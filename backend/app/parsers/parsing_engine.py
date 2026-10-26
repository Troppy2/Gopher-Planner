import re
from typing import Dict, List, Set, Tuple

"""
This file is the PDF extraction engine.
Key-based matching: we match course codes extracted from APAS/transcript PDFs
against the catalog using exact code patterns (e.g., "CSCI 1103").
No ranker is needed, each extracted code either matches a catalog entry or it doesn't.
"""

# Course code pattern: subject code followed by number (e.g., "CSCI 1103", "MATH 1271")
COURSE_CODE_PATTERN = re.compile(
    r"([A-Z][A-Z]*\s+\d{3,4}(?:[A-Z]?\d?)?)\b"
)


def extract_course_codes(text: str) -> Set[str]:
    """Extract unique course codes from APAS/transcript text using key-based matching.

    Returns a set of normalized course codes like {"CSCI 1103", "MATH 1271"}.
    """
    codes: Set[str] = set()
    for match in COURSE_CODE_PATTERN.finditer(text):
        codes.add(match.group(1).strip())
    return codes


def normalize_course_code(code: str) -> str:
    """Normalize a course code: uppercase, collapse whitespace."""
    return " ".join(code.upper().split())


class PDFParser:
    """Parse APAS or transcript PDFs to extract taken, current, and planned courses."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path

    def extract_text(self) -> str:
        import pdfplumber as pdf

        with pdf.open(self.pdf_path) as pdf_file:
            text = ""
            for page in pdf_file.pages:
                text += page.extract_text() + "\n"
        return text

    def _classify_sections(self, text: str) -> Tuple[List[str], List[str], List[str]]:
        """Split APAS course history text into taken, current, and planned sections.

        APAS reports typically have sections labeled "Course History", "In Progress",
        and "Planned" or "Future Term". We use keyword heuristics to split them.
        """
        taken_lines: List[str] = []
        current_lines: List[str] = []
        planned_lines: List[str] = []

        lines = text.split("\n")
        # Heuristic: find section headers
        section_keywords = {
            "taken": {"taken", "completed", "passed"},
            "current": {"in progress", "ip", "currently taking"},
            "planned": {"planned", "future term", "planning"},
        }

        current_section = "taken"# default first section

        for line in lines:
            stripped = line.strip().lower()
            # Detect section header lines
            for sec, keywords in section_keywords.items():
                if any(kw in stripped for kw in keywords) and len(line.strip()) < 80:
                    current_section = sec
                    break
            # Collect lines based on current section
            if current_section == "taken":
                taken_lines.append(line)
            elif current_section in ("current",):
                current_lines.append(line)
            elif current_section == "planned":
                planned_lines.append(line)

        return taken_lines, current_lines, planned_lines

    def find_classes(self, text: str | None = None) -> Dict[str, Set[str]]:
        """Extract taken, current, and planned course codes from APAS text.

        Returns a dict with keys: taken, current, planned — each mapping to a set
        of normalized course codes found in that section.
        """
        if text is None:
            text = self.extract_text()

        taken_lines, current_lines, planned_lines = self._classify_sections(text)

        taken_codes: Set[str] = set()
        current_codes: Set[str] = set()
        planned_codes: Set[str] = set()

        # Key-based matching: extract codes from each section line
        all_sections = [
            ("taken", taken_lines, taken_codes),
            ("current", current_lines, current_codes),
            ("planned", planned_lines, planned_codes),
        ]

        for _section_name, section_lines, section_codes in all_sections:
            for line in section_lines:
                codes = extract_course_codes(line)
                section_codes.update(codes)

        # Normalize all codes
        taken_codes = {normalize_course_code(c) for c in taken_codes}
        current_codes = {normalize_course_code(c) for c in current_codes}
        planned_codes = {normalize_course_code(c) for c in planned_codes}

        return {
            "taken": taken_codes,
            "current": current_codes,
            "planned": planned_codes,
        }