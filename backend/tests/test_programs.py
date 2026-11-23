import importlib.util
import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).parent / "fixtures" / "programs"


def test_loader_accepts_a_synthetic_v2_program_for_the_selected_catalog_term():
    assert importlib.util.find_spec("app.services.programs") is not None, "Missing versioned program loader"
    from app.services.programs import load_program

    expected = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    assert load_program("Synthetic B.S.", "Fall 2026", directory=FIXTURES) == expected


def test_loader_distinguishes_an_unavailable_catalog_version_from_an_unknown_major():
    from app.services import programs

    assert hasattr(programs, "ProgramVersionUnavailable"), "Missing explicit unsupported-version result"
    with pytest.raises(programs.ProgramVersionUnavailable):
        programs.load_program("Synthetic B.S.", "Fall 2025", directory=FIXTURES)
    assert programs.load_program("Unknown major", "Fall 2026", directory=FIXTURES) is None


def test_loader_lists_supported_terms_without_combining_program_versions(tmp_path):
    from app.services import programs

    assert hasattr(programs, "available_catalog_terms"), "Missing supported-version discovery"
    first = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    second = {**first, "catalogTerm": "Fall 2027", "totalCredits": 15,
              "courseMetadata": {code: {**record, "catalogTerm": "Fall 2027"}
                                 for code, record in first["courseMetadata"].items()}}
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(first), encoding="utf-8")
    (tmp_path / "synthetic--fall-2027.json").write_text(json.dumps(second), encoding="utf-8")
    assert programs.available_catalog_terms("Synthetic B.S.", directory=tmp_path) == ["Fall 2026", "Fall 2027"]
    assert programs.available_catalog_terms("Unknown major", directory=tmp_path) == []
    assert programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)["totalCredits"] == 12
    assert programs.load_program("Synthetic B.S.", "Fall 2027", directory=tmp_path)["totalCredits"] == 15


def test_loader_requires_explicit_confirmation_instead_of_selecting_a_candidate_version():
    from app.services import programs

    assert hasattr(programs, "ProgramVersionUnconfirmed"), "Missing explicit unconfirmed-version result"
    with pytest.raises(programs.ProgramVersionUnconfirmed):
        programs.load_program("Synthetic B.S.", None, directory=FIXTURES)
    assert programs.load_program("Unknown major", None, directory=FIXTURES) is None


@pytest.mark.parametrize("change", [
    *[{"remove": field} for field in (
        "schemaVersion", "id", "name", "officialProgramId", "catalogTerm", "totalCredits", "source",
        "sources", "courseSets", "courseMetadata", "groups", "adjustments",
    )],
    {"schemaVersion": 1}, {"schemaVersion": True}, {"unexpected": True}, {"totalCredits": 0},
    {"totalCredits": -1}, {"totalCredits": float("inf")}, {"totalCredits": True}, {"totalCredits": 10**400},
    {"catalogTerm": "Winter 2026"}, {"id": ""}, {"officialProgramId": None}, {"source": ""},
    {"sources": []}, {"courseSets": []}, {"courseMetadata": []}, {"groups": []}, {"adjustments": {}},
])
def test_loader_rejects_malformed_or_unsupported_v2_program_envelopes(tmp_path, change):
    from app.services import programs

    assert hasattr(programs, "ProgramDataError"), "Missing strict v2 schema validation"
    program = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    if "remove" in change:
        del program[change["remove"]]
    else:
        program.update(change)
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(program), encoding="utf-8")
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


@pytest.mark.parametrize("source", [
    {}, {"url": "https://example.invalid", "retrieved": "2026-11-22"},
    {"url": "javascript:bad", "retrieved": "2026-11-22", "section": "Synthetic"},
    {"url": "https://example.invalid", "retrieved": "2026-02-30", "section": "Synthetic"},
    {"url": "https://example.invalid", "retrieved": "20261122", "section": "Synthetic"},
    {"url": "https://example.invalid", "retrieved": "2026-11-22", "section": ""},
    {"url": "https://example.invalid", "retrieved": "2026-11-22", "section": "Synthetic", "extra": True},
])
def test_loader_requires_traceable_source_records_with_real_retrieval_dates(tmp_path, source):
    from app.services import programs

    program = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    program["sources"]["synthetic"] = source
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(program), encoding="utf-8")
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


@pytest.mark.parametrize("rule", [
    None, {},
    {"id": "intro", "type": "unknown", "sourceRef": "synthetic"},
    {"id": "intro", "type": "course", "sourceRef": "missing", "code": "TEST 1001"},
    {"id": "intro", "type": "course", "sourceRef": "synthetic", "code": "bad"},
    {"id": "intro", "type": "course", "sourceRef": "synthetic", "code": "TEST 1001", "extra": 1},
    {"id": "core", "type": "course", "sourceRef": "synthetic", "code": "TEST 1001"},
    {"id": "intro", "type": "all", "sourceRef": "synthetic", "allowReuse": False, "children": []},
    {"id": "intro", "type": "all", "sourceRef": "synthetic", "children": [{"id": "a", "type": "review", "sourceRef": "synthetic", "message": "Synthetic"}]},
    {"id": "intro", "type": "any", "sourceRef": "synthetic", "children": []},
    {"id": "intro", "type": "any", "sourceRef": "synthetic", "children": [
        {"id": "same", "type": "review", "sourceRef": "synthetic", "message": "Synthetic"},
        {"id": "same", "type": "review", "sourceRef": "synthetic", "message": "Synthetic"}]},
    {"id": "intro", "type": "credits", "sourceRef": "synthetic", "courseSet": "missing", "minCredits": 3},
    {"id": "intro", "type": "credits", "sourceRef": "synthetic", "courseSet": "set", "minCredits": 0},
    {"id": "intro", "type": "credits", "sourceRef": "synthetic", "courseSet": "set", "minCredits": True},
    {"id": "intro", "type": "count", "sourceRef": "synthetic", "courseSet": "set"},
    {"id": "intro", "type": "count", "sourceRef": "synthetic", "courseSet": "set", "minCourses": 2, "maxCourses": 1},
    {"id": "intro", "type": "count", "sourceRef": "synthetic", "courseSet": "set", "minCourses": 0.5},
    {"id": "intro", "type": "count", "sourceRef": "synthetic", "courseSet": "set", "maxCourses": True},
    {"id": "intro", "type": "review", "sourceRef": "synthetic", "message": ""},
    {"id": "intro", "type": "course", "sourceRef": "synthetic", "code": "TEST 1001", "gradePolicy": {"minGrade": "Z", "allowS": False, "sourceRef": "synthetic"}},
])
def test_loader_rejects_malformed_requirement_trees_and_global_id_collisions(tmp_path, rule):
    from app.services import programs

    program = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    program["courseSets"]["set"] = {"codes": ["TEST 1001"], "sourceRef": "synthetic"}
    program["groups"][0]["rule"] = rule
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(program), encoding="utf-8")
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


@pytest.mark.parametrize("sets,sharing", [
    ({"set": {"codes": [], "sourceRef": "synthetic"}}, []),
    ({"set": {"codes": ["bad"], "sourceRef": "synthetic"}}, []),
    ({"set": {"codes": ["TEST 1001", "TEST 1001"], "sourceRef": "synthetic"}}, []),
    ({"set": {"codes": ["TEST 1001"], "sourceRef": "missing"}}, []),
    ({"set": {"codes": ["TEST 1001"], "sourceRef": "synthetic", "extra": True}}, []),
    ({}, {}),
    ({}, [{"groups": ["core"], "sourceRef": "synthetic"}]),
    ({}, [{"groups": ["core", "core"], "sourceRef": "synthetic"}]),
    ({}, [{"groups": ["core", "missing"], "sourceRef": "synthetic"}]),
    ({}, [{"groups": ["core", "elective"], "sourceRef": "missing"}]),
    ({}, [{"groups": ["core", "elective"], "sourceRef": "synthetic", "extra": True}]),
    ({}, [{"groups": ["core", "elective"], "sourceRef": "synthetic"},
          {"groups": ["elective", "core"], "sourceRef": "synthetic"}]),
])
def test_loader_rejects_invalid_course_sets_and_unsourced_or_ambiguous_sharing(tmp_path, sets, sharing):
    from app.services import programs

    program = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    program["groups"].append({"id": "elective", "label": "Synthetic elective", "category": "Elective",
                              "sourceRef": "synthetic", "rule": {"id": "elective-review", "type": "review",
                              "sourceRef": "synthetic", "message": "Synthetic review"}})
    program.update(courseSets=sets, sharing=sharing)
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(program), encoding="utf-8")
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


def adjustment_program():
    program = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    program["courseSets"]["set"] = {"codes": ["TEST 1001"], "sourceRef": "synthetic"}
    for suffix in ("one", "two"):
        program["groups"].append({"id": f"group-{suffix}", "label": "Synthetic credits", "category": "Elective",
                                  "sourceRef": "synthetic", "rule": {"id": f"credits-{suffix}", "type": "credits",
                                  "sourceRef": "synthetic", "courseSet": "set", "minCredits": 6}})
    return program


def waiver(*, identity="waiver", triggers=None, effects=None, **extra):
    return {"id": identity, "sourceRef": "synthetic", "whenAnySatisfied": ["intro"] if triggers is None else triggers,
            "effects": [{"targetId": "credits-one", "reduceMinCredits": 4}] if effects is None else effects, **extra}


@pytest.mark.parametrize("adjustments", [
    [waiver(triggers=[])], [waiver(effects=[])], [waiver(triggers=["missing"])],
    [waiver(effects=[{"targetId": "missing", "satisfy": True}])],
    [waiver(effects=[{"targetId": "intro", "reduceMinCredits": 1}])],
    *[[waiver(effects=[{"targetId": "credits-one", "reduceMinCredits": value}])] for value in (0, -1, True, 7)],
    [waiver(effects=[{"targetId": "credits-one", "satisfy": False}])],
    [waiver(effects=[{"targetId": "credits-one", "unsupported": True}])],
    [waiver(identity="intro")], [waiver(), waiver(identity="second")],
    [waiver(triggers=["intro"], effects=[{"targetId": "intro", "satisfy": True}])],
    [waiver(triggers=["core"], effects=[{"targetId": "intro", "satisfy": True}])],
    [waiver(triggers=["credits-two"]), waiver(identity="second", triggers=["credits-one"], effects=[{"targetId": "credits-two", "reduceMinCredits": 4}])],
    [waiver(stackingPolicy="sum")],
])
def test_loader_rejects_unjustified_adjustments_ambiguous_stacking_and_dependency_cycles(tmp_path, adjustments):
    from app.services import programs

    program = adjustment_program()
    program["adjustments"] = adjustments
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(program), encoding="utf-8")
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


@pytest.mark.parametrize("official_name", [None, "", {}, True])
def test_loader_requires_an_optional_official_name_to_be_nonempty_text(tmp_path, official_name):
    from app.services import programs

    program = json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))
    program["officialName"] = official_name
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(program), encoding="utf-8")
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


def write_program(tmp_path, program):
    (tmp_path / "synthetic--fall-2026.json").write_text(json.dumps(program), encoding="utf-8")


def base_program():
    return json.loads((FIXTURES / "synthetic--fall-2026.json").read_text(encoding="utf-8"))


VALID_RECORD = {"catalogTerm": "Fall 2026", "title": "Synthetic introduction", "minimumCredits": 3,
                "maximumCredits": 3, "offered": ["Fall", "Spring"],
                "prerequisites": {"expression": None, "sourceRef": "synthetic"}, "sourceRef": "synthetic"}


@pytest.mark.parametrize("change", [
    {"remove": "title"}, {"remove": "prerequisites"}, {"extra": True}, {"catalogTerm": "Fall 2027"},
    {"catalogTerm": None}, {"title": ""}, {"title": 3}, {"minimumCredits": -1}, {"minimumCredits": True},
    {"maximumCredits": float("nan")}, {"minimumCredits": 4, "maximumCredits": 3}, {"offered": []},
    {"offered": ["Fall", "Fall"]}, {"offered": ["Winter"]}, {"offered": "Fall"}, {"sourceRef": "missing"},
    {"prerequisites": {"expression": None}}, {"prerequisites": {"expression": None, "sourceRef": "missing"}},
    {"prerequisites": {"expression": None, "sourceRef": "synthetic", "extra": 1}},
    {"prerequisites": {"expression": {"type": "unknown"}, "sourceRef": "synthetic"}},
    {"prerequisites": {"expression": {"type": "course", "course_code": "bad"}, "sourceRef": "synthetic"}},
    {"prerequisites": {"expression": {"type": "all_of", "requirements": []}, "sourceRef": "synthetic"}},
    {"prerequisites": {"expression": {"type": "any_of", "requirements": [{"type": "condition", "text": ""}]}, "sourceRef": "synthetic"}},
    {"prerequisites": {"expression": {"type": "course", "course_code": "TEST 1002", "extra": 1}, "sourceRef": "synthetic"}},
])
def test_loader_rejects_unsourced_or_malformed_supplemental_course_metadata(tmp_path, change):
    from app.services import programs

    program = base_program()
    record = dict(VALID_RECORD)
    if "remove" in change:
        del record[change["remove"]]
    else:
        record.update(change)
    program["courseMetadata"]["TEST 1001"] = record
    write_program(tmp_path, program)
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


def test_loader_rejects_supplemental_metadata_keyed_by_an_invalid_course_code(tmp_path):
    from app.services import programs

    program = base_program()
    program["courseMetadata"]["not a code"] = dict(VALID_RECORD)
    write_program(tmp_path, program)
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


@pytest.mark.parametrize("compatibility", [
    {}, [{}], [{"catalogVersion": "unknown", "catalogTerm": "Fall 2026", "sourceRef": "synthetic"}],
    [{"catalogVersion": "", "catalogTerm": "Fall 2026", "sourceRef": "synthetic"}],
    [{"catalogVersion": "2026-27", "catalogTerm": "Fall 2027", "sourceRef": "synthetic"}],
    [{"catalogVersion": "2026-27", "catalogTerm": "Fall 2026", "sourceRef": "missing"}],
    [{"catalogVersion": "2026-27", "catalogTerm": "Fall 2026", "sourceRef": "synthetic", "extra": 1}],
    [{"catalogVersion": "2026-27", "catalogTerm": "Fall 2026", "sourceRef": "synthetic"},
     {"catalogVersion": "2026-27", "catalogTerm": "Fall 2026", "sourceRef": "synthetic"}],
])
def test_loader_rejects_invalid_or_unverified_catalog_compatibility(tmp_path, compatibility):
    from app.services import programs

    program = base_program()
    program["catalogCompatibility"] = compatibility
    write_program(tmp_path, program)
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


def test_loader_accepts_every_documented_expression_sharing_adjustment_and_metadata_shape():
    from app.services import programs

    program = programs.load_program("Rich Synthetic B.S.", "Fall 2026", directory=FIXTURES)
    kinds = set()

    def walk(rule):
        kinds.add(rule["type"])
        for child in rule.get("children", []):
            walk(child)

    for group in program["groups"]:
        walk(group["rule"])
    assert kinds == {"course", "all", "any", "credits", "count", "review"}
    assert program["sharing"] and program["adjustments"] and program["catalogCompatibility"]
    expressions = {record["prerequisites"]["expression"]["type"] for record in program["courseMetadata"].values()
                   if record["prerequisites"] and record["prerequisites"]["expression"]}
    assert expressions == {"course", "all_of", "any_of", "condition"}
    assert any(record["prerequisites"] is None for record in program["courseMetadata"].values())
    assert any(record["offered"] is None for record in program["courseMetadata"].values())


def test_loader_caches_validated_versions_until_the_cache_is_cleared(tmp_path):
    from app.services import programs

    program = base_program()
    write_program(tmp_path, program)
    programs.clear_program_cache()
    assert programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)["totalCredits"] == 12
    write_program(tmp_path, {**program, "totalCredits": 18})
    assert programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)["totalCredits"] == 12
    programs.clear_program_cache()
    assert programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)["totalCredits"] == 18


def test_loader_caches_each_directory_independently(tmp_path):
    from app.services import programs

    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir(), second.mkdir()
    write_program(first, base_program())
    write_program(second, {**base_program(), "totalCredits": 24})
    programs.clear_program_cache()
    assert programs.load_program("Synthetic B.S.", "Fall 2026", directory=first)["totalCredits"] == 12
    assert programs.load_program("Synthetic B.S.", "Fall 2026", directory=second)["totalCredits"] == 24


def test_loader_returns_copies_so_callers_cannot_corrupt_the_cache(tmp_path):
    from app.services import programs

    write_program(tmp_path, base_program())
    programs.clear_program_cache()
    programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)["groups"].clear()
    assert programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)["groups"]


def test_loader_rejects_ambiguous_duplicate_registrations_of_one_program_version(tmp_path):
    from app.services import programs

    write_program(tmp_path, base_program())
    (tmp_path / "copy--fall-2026.json").write_text(json.dumps({**base_program(), "id": "copy"}), encoding="utf-8")
    programs.clear_program_cache()
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


def test_loader_requires_file_names_to_match_program_id_and_catalog_term(tmp_path):
    from app.services import programs

    (tmp_path / "synthetic--spring-2027.json").write_text(json.dumps(base_program()), encoding="utf-8")
    programs.clear_program_cache()
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)


def test_one_malformed_seed_file_fails_every_lookup_in_that_directory_loudly(tmp_path):
    from app.services import programs

    write_program(tmp_path, base_program())
    (tmp_path / "broken--fall-2026.json").write_text("{not json", encoding="utf-8")
    programs.clear_program_cache()
    with pytest.raises(programs.ProgramDataError):
        programs.load_program("Synthetic B.S.", "Fall 2026", directory=tmp_path)
