"""Official four-year sample plans (sampleplan.umn.edu), loaded per program and mapped onto real terms."""
import json
import os
from functools import lru_cache
from pathlib import Path

from app.services.planning.terms import PLAN_TERM

SAMPLE_DIRECTORY = Path(__file__).resolve().parents[3] / "data" / "sample_plans"
ORDER = [(year, season) for year in range(1, 5) for season in ("Fall", "Spring")]


def sample_directory():
    return Path(os.environ.get("SAMPLE_PLAN_DATA_PATH") or SAMPLE_DIRECTORY)


@lru_cache(maxsize=256)
def _load(directory, program_id):
    path = Path(directory) / f"{program_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_sample_plan(program_id):
    """The sample plan for a program id, or None when the site publishes none."""
    if not program_id:
        return None
    return _load(str(sample_directory()), program_id)


def sample_terms(graduation):
    """Map (year, season) of a four-year sample plan to real terms ending at ``graduation``.

    Spring graduation: Year 1 Fall is four years earlier. Fall graduation: Year 4 Fall is the graduation term."""
    if not isinstance(graduation, str) or not PLAN_TERM.fullmatch(graduation):
        return {}
    name, year = graduation.split()
    start = int(year) - 4 if name == "Spring" else int(year) - 3
    mapping = {}
    for index, (plan_year, season) in enumerate(ORDER):
        calendar_year = start + (index + 1) // 2
        mapping[(plan_year, season)] = f"{season} {calendar_year}"
    return mapping
