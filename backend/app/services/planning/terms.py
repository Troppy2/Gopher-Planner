"""Academic term arithmetic. Plans use Fall and Spring only; Summer only orders past coursework."""
import re

SEASON_INDEX = {"Spring": 0, "Summer": 1, "Fall": 2}
PLAN_TERM = re.compile(r"^(Fall|Spring) [1-9]\d{3}$")


def season(term):
    return term.split()[0]


def term_index(term):
    name, year = term.split()
    return int(year) * 3 + SEASON_INDEX[name]


def current_term(today):
    return f"{'Spring' if today.month <= 5 else 'Fall'} {today.year}"


def next_term(term):
    name, year = term.split()
    return f"Spring {int(year) + 1}" if name == "Fall" else f"Fall {year}"


def future_terms(start, count):
    terms, term = [], start
    for _ in range(count):
        term = next_term(term)
        terms.append(term)
    return terms


def plan_window(current, target, *, default=8, maximum=12):
    """Future terms through a valid future graduation target, otherwise ``default`` terms; never more than ``maximum``."""
    if isinstance(target, str) and PLAN_TERM.fullmatch(target) and term_index(target) > term_index(current):
        terms = []
        term = current
        while term_index(term) < term_index(target) and len(terms) < maximum:
            term = next_term(term)
            terms.append(term)
        return terms
    return future_terms(current, default)
