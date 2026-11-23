"""Version-specific program seed files, separate from user persistence."""
import copy
import json
import os
from pathlib import Path

from app.schemas.programs import ProgramDataError, validate_program


PROGRAM_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "programs"
# Official program ids whose requirements were checked rule by rule (scripts/program_overlays).
# Every other program is machine-mapped and shown to students as unverified.
REVIEWED_PROGRAM_IDS = frozenset({"019627107"})
SEASON_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}

# Validated programs keyed by resolved directory, then by (name, catalog term).
_CACHE: dict[Path, dict[tuple[str, str], dict]] = {}


class ProgramVersionUnavailable(ValueError):
    pass


class ProgramVersionUnconfirmed(ValueError):
    pass


def clear_program_cache():
    _CACHE.clear()


def term_slug(term):
    return term.lower().replace(" ", "-")


def term_sort_key(term):
    season, year = term.split()
    return int(year), SEASON_ORDER[season]


def program_directory():
    return Path(os.environ.get("PROGRAM_DATA_PATH") or PROGRAM_DIRECTORY)


def _index(directory):
    """Validate every seed file once. Any malformed or ambiguous file fails all lookups loudly."""
    key = Path(directory or program_directory()).resolve()
    if key not in _CACHE:
        index = {}
        for path in sorted(key.glob("*.json")):
            try:
                program = validate_program(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as error:
                raise ProgramDataError(f"Program file {path.name} is not valid JSON") from error
            if path.name != f"{program['id']}--{term_slug(program['catalogTerm'])}.json":
                raise ProgramDataError(f"Program file {path.name} does not match its id and catalog term")
            identity = (program["name"], program["catalogTerm"])
            if identity in index:
                raise ProgramDataError(f"Duplicate registrations for {identity[0]} {identity[1]}")
            index[identity] = program
        _CACHE[key] = index
    return _CACHE[key]


def program_names(*, directory=None):
    return sorted({name for name, _ in _index(directory)})


def available_catalog_terms(major, *, directory=None):
    return sorted({term for name, term in _index(directory) if name == major}, key=term_sort_key)


def load_program(major, catalog_term, *, directory=None):
    index = _index(directory)
    program = index.get((major, catalog_term))
    if program is not None:
        return copy.deepcopy(program)
    if any(name == major for name, _ in index):
        if catalog_term is None:
            raise ProgramVersionUnconfirmed("Select a supported catalog term before applying program requirements")
        raise ProgramVersionUnavailable("The requested program catalog version is unavailable")
    return None


def list_programs(*, directory=None):
    """Supported programs for selection: profile name, official name and catalog terms, without requirements."""
    index = _index(directory)
    names = sorted({name for name, _ in index})
    return [{"name": name,
             "officialName": next(program.get("officialName", name) for (other, _), program in index.items() if other == name),
             "catalogTerms": available_catalog_terms(name, directory=directory),
             "reviewed": any(program.get("officialProgramId") in REVIEWED_PROGRAM_IDS
                             for (other, _), program in index.items() if other == name)} for name in names]
