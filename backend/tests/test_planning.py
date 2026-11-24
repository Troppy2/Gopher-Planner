"""Pure planning engine tests: synthetic, hand-checkable, no Flask app or database."""
import copy
import json
from datetime import date
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "programs"
TERMS = ["Spring 2027", "Fall 2027", "Spring 2028", "Fall 2028"]


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def metadata_for(program):
    from app.services.metadata import resolve_course
    return {code: resolve_course(code, program, None) for code in program["courseMetadata"]}


def generate(program, coursework=(), *, load_limit=7, terms=TERMS, base=0, status="ok", metadata=None):
    from app.services.planning.generate import generate_plan
    return generate_plan(program, coursework=list(coursework), metadata=metadata or (metadata_for(program) if program else {}),
                         terms=terms, credit_load=load_limit, base_credits=base, status=status)


def placed(result):
    return {item["code"]: item["term"] for item in result["placements"]}


def done(code, credits=3, grade="A", term="Fall 2025", status="done"):
    return {"code": code, "credits": credits, "grade": grade, "term": term, "status": status}


# terms.py

@pytest.mark.parametrize("today,term", [(date(2026, 5, 31), "Spring 2026"), (date(2026, 6, 1), "Fall 2026"),
                                        (date(2026, 12, 31), "Fall 2026"), (date(2027, 1, 1), "Spring 2027")])
def test_current_term_boundaries(today, term):
    from app.services.planning.terms import current_term
    assert current_term(today) == term


def test_future_terms_alternate_fall_and_spring_across_year_rollover_without_summer():
    from app.services.planning.terms import future_terms, season, term_index
    assert future_terms("Fall 2026", 3) == ["Spring 2027", "Fall 2027", "Spring 2028"]
    assert future_terms("Spring 2027", 2) == ["Fall 2027", "Spring 2028"]
    assert season("Spring 2027") == "Spring"
    assert term_index("Spring 2027") < term_index("Summer 2027") < term_index("Fall 2027") < term_index("Spring 2028")


def test_plan_window_extends_to_a_valid_future_graduation_target_with_limits():
    from app.services.planning.terms import plan_window
    assert plan_window("Fall 2026", "Fall 2028") == ["Spring 2027", "Fall 2027", "Spring 2028", "Fall 2028"]
    assert len(plan_window("Fall 2026", "")) == 8
    assert len(plan_window("Fall 2026", "Spring 2026")) == 8
    assert len(plan_window("Fall 2026", "Fall 2040")) == 12
    assert len(plan_window("Fall 2026", "Summer 2028")) == 8


# prerequisites.py

def prereq(expression, state="tree"):
    return {"state": state, "expression": expression}


def course(code):
    return {"type": "course", "course_code": code}


def check(expression, *, done_codes=(), progress=(), planned=None, at=5, state="tree"):
    from app.services.planning.prerequisites import evaluate_prerequisites
    return evaluate_prerequisites(prereq(expression, state), done=set(done_codes), in_progress=set(progress),
                                  planned=planned or {}, term=at)


def test_course_prerequisites_accept_done_in_progress_or_strictly_earlier_planned_courses():
    assert check(course("A 1001"), done_codes={"A 1001"}).ok
    assert check(course("A 1001"), progress={"A 1001"}).ok
    assert check(course("A 1001"), planned={"A 1001": 4}).ok
    assert not check(course("A 1001"), planned={"A 1001": 5}).ok
    assert not check(course("A 1001"), planned={"A 1001": 6}).ok
    assert check(course("A 1001"), planned={"A 1001": 6}).missing == ["A 1001"]


def test_nested_all_and_any_prerequisite_trees():
    tree = {"type": "all_of", "requirements": [course("A 1001"), {"type": "any_of", "requirements": [course("B 1001"), course("C 1001")]}]}
    assert check(tree, done_codes={"A 1001", "C 1001"}).ok
    assert not check(tree, done_codes={"A 1001"}).ok
    assert check(tree, done_codes={"A 1001"}).missing == ["B 1001"]


def test_conditions_are_nonblocking_but_require_review():
    result = check({"type": "all_of", "requirements": [course("A 1001"), {"type": "condition", "text": "Standing"}]}, done_codes={"A 1001"})
    assert result.ok and result.review


def test_verified_empty_prerequisites_differ_from_unknown_prerequisites():
    assert check(None, state="verified_none").ok
    unknown = check(None, state="unknown")
    assert not unknown.ok and unknown.unknown


# eligibility.py

def meta(offered=("Fall", "Spring"), state="verified_none", expression=None, blocked=None, warnings=()):
    return {"code": "X 1001", "title": "X", "minimumCredits": 3, "maximumCredits": 3, "offered": list(offered) if offered else None,
            "prerequisites": {"state": state, "expression": expression}, "metadataSource": "program",
            "metadataWarnings": list(warnings), "blockedReason": blocked}


def eligible(record, term="Fall 2027", **kwargs):
    from app.services.planning.eligibility import placement_check
    return placement_check(record, term, TERMS.index(term), done=kwargs.get("done", set()), in_progress=kwargs.get("progress", set()),
                           planned=kwargs.get("planned", {}))


def test_known_season_mismatch_blocks_and_unknown_offering_is_tentative():
    assert eligible(meta(offered=("Spring",))).reason == "not_offered_in_season"
    tentative = eligible(meta(offered=None))
    assert tentative.ok and "offered_terms_unverified" in tentative.warnings


def test_missing_prerequisite_metadata_or_conflicts_block_placement():
    assert eligible(meta(state="unknown", blocked="course_metadata_unavailable")).reason == "course_metadata_unavailable"
    assert eligible(meta(blocked="catalog_metadata_conflict")).reason == "course_metadata_unavailable"


def test_same_term_prerequisites_do_not_count_but_in_progress_ones_do():
    record = meta(state="tree", expression=course("A 1001"))
    assert eligible(record, planned={"A 1001": 1}).reason == "prerequisite_not_before"
    assert eligible(record, planned={"A 1001": 0}).ok
    assert eligible(record, progress={"A 1001"}).ok


# generate.py

def test_unknown_unsupported_and_unconfirmed_programs_yield_no_placements_with_distinct_warnings():
    assert generate(None, status="unknown") == {"placements": [], "warnings": ["program_requirements_unavailable"], "requirementProgress": []}
    assert generate(None, status="unavailable")["warnings"] == ["program_version_unavailable"]
    assert generate(None, status="unconfirmed")["warnings"] == ["program_version_unconfirmed"]


def test_four_term_program_switches_to_a_second_complete_branch_when_the_first_is_infeasible():
    result = generate(load("mini-synthetic--fall-2026.json"))
    assert placed(result) == {"MINI 1101": "Spring 2027", "MATH 3101": "Spring 2027", "MINI 1102": "Fall 2027",
                              "MINI 2001": "Spring 2028", "MINI 3001": "Fall 2028"}
    assert "MINI 1001" not in placed(result)
    progress = {item["id"]: item for item in result["requirementProgress"]}
    assert progress["second-sequence"]["projectedStatus"] == "satisfied"
    assert progress["first-sequence"]["projectedStatus"] == "unsatisfied"
    assert all(progress[group]["projectedStatus"] == "satisfied" for group in ("core", "math", "electives"))
    assert set(result["warnings"]) == {"offered_terms_unverified", "graduation_target_unreachable"}


def test_generation_never_exceeds_the_credit_load_or_places_before_prerequisites():
    program = load("mini-synthetic--fall-2026.json")
    result = generate(program)
    metadata = metadata_for(program)
    loads = {}
    for item in result["placements"]:
        loads[item["term"]] = loads.get(item["term"], 0) + metadata[item["code"]]["minimumCredits"]
    assert max(loads.values()) <= 7
    order = {item["code"]: TERMS.index(item["term"]) for item in result["placements"]}
    assert order["MINI 1101"] < order["MINI 1102"] < order["MINI 3001"]


def test_completed_and_in_progress_courses_are_never_placed_and_count_toward_requirements():
    program = load("mini-synthetic--fall-2026.json")
    result = generate(program, [done("MINI 1101"), done("MINI 1102", 4, None, "Fall 2026", "prog")], base=3)
    assert "MINI 1101" not in placed(result) and "MINI 1102" not in placed(result)
    assert placed(result)["MINI 2001"] == "Spring 2027"
    assert placed(result)["MINI 3001"] == "Fall 2027"


def test_generation_is_deterministic_and_does_not_mutate_inputs():
    program, coursework = load("mini-synthetic--fall-2026.json"), [done("MINI 1101")]
    metadata = metadata_for(program)
    snapshot = copy.deepcopy((program, coursework, metadata))
    first = generate(program, coursework, metadata=metadata)
    assert first == generate(program, coursework, metadata=metadata)
    assert (program, coursework, metadata) == snapshot


def inline(groups, *, sets=None, adjustments=None, total=12, metadata=None):
    from app.schemas.programs import validate_program
    records = metadata or {}
    return validate_program({
        "schemaVersion": 2, "id": "inline", "name": "Inline B.S.", "officialProgramId": "inline", "catalogTerm": "Fall 2026",
        "totalCredits": total, "source": "Synthetic",
        "sources": {"s": {"url": "https://example.invalid", "retrieved": "2026-11-22", "section": "Synthetic"}},
        "courseSets": sets or {}, "sharing": [], "adjustments": adjustments or [], "groups": groups,
        "courseMetadata": {code: {"catalogTerm": "Fall 2026", "title": code, "minimumCredits": 3, "maximumCredits": 3,
                                  "offered": ["Fall", "Spring"], "prerequisites": {"expression": None, "sourceRef": "s"},
                                  "sourceRef": "s", **records.get(code, {})}
                           for code in sorted({*records, *(c for s in (sets or {}).values() for c in s["codes"]), *[
                               c for g in groups for c in _codes(g["rule"])]})},
    })


def _codes(rule):
    if rule["type"] == "course":
        return [rule["code"]]
    return [code for child in rule.get("children", []) for code in _codes(child)]


POLICY = {"minGrade": "C-", "allowS": False, "sourceRef": "s"}


def grp(identity, rule, category="Major core"):
    return {"id": identity, "label": identity, "category": category, "sourceRef": "s", "gradePolicy": POLICY, "rule": rule}


def crs(identity, code):
    return {"id": identity, "type": "course", "code": code, "sourceRef": "s"}


def test_reaching_the_credit_goal_does_not_hide_a_missing_required_course():
    program = inline([grp("core", crs("needed", "REQ 1001"))], total=6, metadata={"REQ 1001": {"prerequisites": None}})
    result = generate(program, [done("OLD 1001", 6)], base=6)
    assert result["placements"] == []
    assert {"requirements_incomplete", "course_metadata_unavailable"} <= set(result["warnings"])
    assert "graduation_target_unreachable" not in result["warnings"]
    assert result["requirementProgress"][0]["projectedStatus"] == "unsatisfied"


def waiver_program(with_waiver):
    sets = {"electives": {"codes": ["ELEC 3001", "ELEC 3002"], "sourceRef": "s"}}
    route = {"id": "route", "type": "any", "sourceRef": "s", "children": [
        {"id": "long", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [crs("l1", "LONG 1001"), crs("l2", "LONG 1002")]},
        crs("substitute", "SUB 1001")]}
    adjustments = [{"id": "waiver", "sourceRef": "s", "whenAnySatisfied": ["substitute"],
                    "effects": [{"targetId": "elective-credits", "reduceMinCredits": 3}]}] if with_waiver else []
    return inline([grp("core", route), grp("electives", {"id": "elective-credits", "type": "credits", "courseSet": "electives",
                                                        "minCredits": 6, "sourceRef": "s"}, "Elective")],
                  sets=sets, adjustments=adjustments)


def test_justified_waiver_reduces_the_courses_generation_adds():
    with_waiver, without = placed(generate(waiver_program(True))), placed(generate(waiver_program(False)))
    assert "SUB 1001" in with_waiver and "SUB 1001" in without
    assert sum(code.startswith("ELEC") for code in with_waiver) == 1
    assert sum(code.startswith("ELEC") for code in without) == 2


def test_unmet_subject_quota_is_reported_when_its_only_options_cannot_be_scheduled():
    sets = {"all": {"codes": ["SUBJ 3001", "SUBJ 3002", "OTHR 3001"], "sourceRef": "s"},
            "subject": {"codes": ["SUBJ 3001", "SUBJ 3002"], "sourceRef": "s"}}
    rule = {"id": "rules", "type": "all", "allowReuse": True, "sourceRef": "s", "children": [
        {"id": "total", "type": "credits", "courseSet": "all", "minCredits": 6, "sourceRef": "s"},
        {"id": "subject-min", "type": "credits", "courseSet": "subject", "minCredits": 6, "sourceRef": "s"}]}
    program = inline([grp("electives", rule, "Elective")], sets=sets, metadata={"SUBJ 3002": {"prerequisites": None}})
    result = generate(program)
    progress = {item["id"]: item for item in result["requirementProgress"]}
    assert progress["subject-min"]["projectedStatus"] == "unsatisfied"
    assert progress["total"]["projectedStatus"] == "satisfied"
    assert "requirements_incomplete" in result["warnings"]
    assert "SUBJ 3002" not in placed(result)


def test_incomplete_metadata_yields_an_honest_partial_plan():
    program = inline([grp("core", {"id": "both", "type": "all", "allowReuse": False, "sourceRef": "s",
                                   "children": [crs("ok", "GOOD 1001"), crs("bad", "BAD 1001")]})],
                     metadata={"BAD 1001": {"prerequisites": None}})
    result = generate(program)
    assert placed(result) == {"GOOD 1001": "Spring 2027"}
    assert {"requirements_incomplete", "course_metadata_unavailable"} <= set(result["warnings"])


# validate.py

def validate(planned, *, locked=None, changed=(), program=None):
    from app.services.planning.validate import validate_plan
    program = program or load("mini-synthetic--fall-2026.json")
    return validate_plan(planned, locked=locked or {}, metadata=metadata_for(program), terms=TERMS, changed=set(changed))


def test_validation_accepts_a_valid_partial_plan():
    assert validate({"MINI 1101": "Spring 2027"}) == []


def test_validation_reports_wrong_season_prerequisite_order_locked_courses_and_missing_metadata():
    violations = validate({"MINI 2001": "Fall 2027", "MINI 1102": "Spring 2027", "MINI 1101": "Spring 2027", "MINI 1002": "Fall 2027"},
                          locked={"MINI 1001": "done"}, changed={"MINI 1001"})
    assert {"code": "MINI 2001", "reason": "not_offered_in_season", "detail": "Fall"} in violations
    assert {"code": "MINI 1102", "reason": "prerequisite_not_before", "detail": "MINI 1101"} in violations
    assert {"code": "MINI 1001", "reason": "locked_course", "detail": "done"} in violations
    assert {"code": "MINI 1002", "reason": "course_metadata_unavailable", "detail": "course_metadata_unavailable"} in violations


def test_moving_a_prerequisite_later_flags_its_dependent():
    violations = validate({"MINI 1101": "Fall 2027", "MINI 1102": "Fall 2027"})
    assert violations == [{"code": "MINI 1102", "reason": "prerequisite_not_before", "detail": "MINI 1101"}]


def test_a_review_only_alternative_does_not_stop_planning_the_machine_checkable_branch():
    rule = {"id": "arch", "type": "any", "sourceRef": "s", "children": [
        crs("standard", "ARCH 2021"), {"id": "exception", "type": "review", "message": "Double majors only", "sourceRef": "s"}]}
    assert placed(generate(inline([grp("core", rule)]))) == {"ARCH 2021": "Spring 2027"}


def test_unverified_grade_policy_does_not_cause_over_planning():
    from app.schemas.programs import validate_program

    program = inline([grp("electives", {"id": "pool", "type": "credits", "courseSet": "pool", "minCredits": 6, "sourceRef": "s"}, "Elective")],
                     sets={"pool": {"codes": ["POOL 1001", "POOL 1002", "POOL 1003"], "sourceRef": "s"}})
    del program["groups"][0]["gradePolicy"]
    validate_program(program)
    result = generate(program)
    assert len(result["placements"]) == 2
    assert result["requirementProgress"][0]["projectedStatus"] == "needs_review"


def test_branch_ranking_counts_one_option_of_each_alternative_not_all_of_them():
    short = {"id": "a-short", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [
        {"id": "a-choice", "type": "any", "sourceRef": "s", "children": [crs("x", "XXXX 1001"), crs("y", "YYYY 1001")]},
        crs("z", "ZZZZ 1001")]}
    long = {"id": "b-long", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [crs("p", "PPPP 1001"), crs("q", "QQQQ 1001")]}
    program = inline([grp("core", {"id": "options", "type": "any", "sourceRef": "s", "children": [long, short]})],
                     metadata={"PPPP 1001": {"minimumCredits": 4, "maximumCredits": 4}, "QQQQ 1001": {"minimumCredits": 4, "maximumCredits": 4}})
    assert set(placed(generate(program))) == {"XXXX 1001", "ZZZZ 1001"}


def test_elective_pools_prefer_the_home_subject_over_alphabetical_order():
    core = crs("major-1001", "MAJR 1001")
    pool = {"id": "pool", "type": "credits", "courseSet": "pool", "minCredits": 3, "sourceRef": "s"}
    program = inline([grp("core", core), grp("electives", pool, "Elective")],
                     sets={"pool": {"codes": ["AAAA 4001", "MAJR 4001"], "sourceRef": "s"}})
    assert set(placed(generate(program))) == {"MAJR 1001", "MAJR 4001"}


def test_elective_pools_avoid_options_that_drag_in_extra_prerequisites():
    pool = {"id": "pool", "type": "credits", "courseSet": "pool", "minCredits": 3, "sourceRef": "s"}
    program = inline([grp("electives", pool, "Elective")],
                     sets={"pool": {"codes": ["POOL 4001", "POOL 4002"], "sourceRef": "s"}},
                     metadata={"POOL 4001": {"prerequisites": {"expression": {"type": "course", "course_code": "PRE 1001"}, "sourceRef": "s"}},
                               "PRE 1001": {}})
    assert set(placed(generate(program))) == {"POOL 4002"}


def test_elective_pools_prefer_lower_level_courses_when_otherwise_equal():
    pool = {"id": "pool", "type": "credits", "courseSet": "pool", "minCredits": 3, "sourceRef": "s"}
    program = inline([grp("electives", pool, "Elective")], sets={"pool": {"codes": ["POOL 5001", "POOL 4001"], "sourceRef": "s"}})
    assert set(placed(generate(program))) == {"POOL 4001"}


@pytest.mark.parametrize("marker", [{"preferred": True}, {"label": "Physics II (Preferred)"}])
def test_preferred_branch_wins_over_a_cheaper_alternative(marker):
    physics = {"id": "b-physics", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [crs("p", "PHYS 1302")], **marker}
    other = {"id": "a-other", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [crs("o", "ESCI 2201")]}
    program = inline([grp("core", {"id": "science", "type": "any", "sourceRef": "s", "children": [other, physics]})],
                     metadata={"PHYS 1302": {"minimumCredits": 4, "maximumCredits": 4}})
    assert set(placed(generate(program))) == {"PHYS 1302"}


def test_without_a_preference_the_cheaper_branch_still_wins():
    physics = {"id": "b-physics", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [crs("p", "PHYS 1302")]}
    other = {"id": "a-other", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [crs("o", "ESCI 2201")]}
    program = inline([grp("core", {"id": "science", "type": "any", "sourceRef": "s", "children": [physics, other]})],
                     metadata={"PHYS 1302": {"minimumCredits": 4, "maximumCredits": 4}})
    assert set(placed(generate(program))) == {"ESCI 2201"}


def test_program_preferred_courses_win_inside_a_pool():
    pool = {"id": "pool", "type": "credits", "courseSet": "pool", "minCredits": 3, "sourceRef": "s"}
    program = inline([grp("electives", pool, "Elective")], sets={"pool": {"codes": ["PHYS 1222", "PHYS 1302W"], "sourceRef": "s"}})
    program["preferredCourses"] = ["PHYS 1302W"]
    assert set(placed(generate(program))) == {"PHYS 1302W"}


# Sample-plan seeding.

def sample(*terms):
    return {"programId": "inline", "plan": "Inline", "source": "https://example.invalid", "retrieved": "2026-11-23",
            "terms": [{"year": year, "season": season, "items": items} for year, season, items in terms]}


def test_sample_plan_terms_map_back_from_the_graduation_term():
    from app.services.planning.sample import sample_terms
    assert sample_terms("Spring 2029") == {(1, "Fall"): "Fall 2025", (1, "Spring"): "Spring 2026",
                                           (4, "Fall"): "Fall 2028", (4, "Spring"): "Spring 2029",
                                           (2, "Fall"): "Fall 2026", (2, "Spring"): "Spring 2027",
                                           (3, "Fall"): "Fall 2027", (3, "Spring"): "Spring 2028"}


def seeded(program, plan, coursework=(), *, suggest=None, coverage=frozenset(), metadata=None, load_limit=7):
    from app.services.planning.generate import generate_plan
    return generate_plan(program, coursework=list(coursework), metadata=metadata or metadata_for(program), terms=TERMS,
                         credit_load=load_limit, sample=plan, graduation="Fall 2028", le_suggest=suggest, le_coverage=coverage)


def test_sample_courses_land_in_their_sample_term_and_requirements_fill_the_rest():
    rule = {"id": "core", "type": "all", "allowReuse": False, "sourceRef": "s",
            "children": [crs("a", "MAJR 1001"), crs("b", "MAJR 2001")]}
    program = inline([grp("major", rule)])
    plan = sample((3, "Fall", [{"kind": "course", "codes": ["MAJR 1001"], "credits": 3, "preferred": False}]))
    assert placed(seeded(program, plan)) == {"MAJR 1001": "Fall 2027", "MAJR 2001": "Spring 2027"}


def test_sample_courses_for_already_met_requirements_are_skipped():
    choice = {"id": "calc", "type": "any", "sourceRef": "s", "children": [crs("c1", "MATH 1271"), crs("c2", "MATH 1371")]}
    program = inline([grp("major", choice)])
    plan = sample((3, "Fall", [{"kind": "course", "codes": ["MATH 1371"], "credits": 3, "preferred": True}]))
    assert placed(seeded(program, plan, [done("MATH 1271")])) == {}


def test_past_sample_terms_are_skipped_but_unmet_requirements_are_still_planned():
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    plan = sample((1, "Fall", [{"kind": "course", "codes": ["MAJR 1001"], "credits": 3, "preferred": False},
                               {"kind": "course", "codes": ["XTRA 1001"], "credits": 1, "preferred": False}]))
    result = seeded(program, plan, metadata={**metadata_for(program), "XTRA 1001": metadata_for(inline([grp("xg", crs("xc", "XTRA 1001"))]))["XTRA 1001"]})
    assert placed(result) == {"MAJR 1001": "Spring 2027"}


def test_le_slots_get_a_suggested_course_unless_already_covered():
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    extra = metadata_for(inline([grp("xg", {"id": "xr", "type": "all", "allowReuse": False, "sourceRef": "s",
                                           "children": [crs("g", "GLOB 1001"), crs("h", "HIST 1001")]})]))
    calls = []

    def suggest(categories, term, exclude):
        calls.append((tuple(categories), term))
        code = "GLOB 1001" if "Global Perspectives" in categories else "HIST 1001"
        return code, extra[code], categories

    plan = sample((3, "Fall", [{"kind": "le", "categories": ["Global Perspectives"], "credits": 3, "label": "Global Perspectives"},
                               {"kind": "le", "categories": ["Historical Perspectives"], "credits": 3, "label": "Historical Perspectives"}]))
    result = seeded(program, plan, suggest=suggest, coverage=frozenset({"Historical Perspectives"}))
    assert calls == [(("Global Perspectives",), "Fall 2027")]
    slots = {item["code"]: item.get("slot") for item in result["placements"]}
    assert slots == {"GLOB 1001": "Global Perspectives", "MAJR 1001": None}
    assert placed(result)["GLOB 1001"] == "Fall 2027"


def test_free_elective_credits_report_what_is_left_to_reach_the_total():
    program = inline([grp("major", crs("a", "MAJR 1001"))], total=12)
    result = seeded(program, sample())
    assert result["electiveCredits"] == 9.0


def test_one_le_slot_can_need_two_separate_suggestions():
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    extra = metadata_for(inline([grp("x", {"id": "r", "type": "all", "allowReuse": False, "sourceRef": "s",
        "children": [crs("g", "SYN 1001"), crs("h", "SYN 1002")]})]))
    def suggest(categories, term, exclude):
        category = categories[0]
        code = "SYN 1001" if category == "Synthetic arts" else "SYN 1002"
        return code, extra[code], [category]
    plan = sample((3, "Fall", [{"kind": "le", "categories": ["Synthetic arts", "Synthetic history"], "label": "Synthetic breadth"}]))
    result = seeded(program, plan, suggest=suggest, load_limit=15)
    assert {p["code"] for p in result["placements"] if p.get("slot")} == {"SYN 1001", "SYN 1002"}


def test_sample_plan_preserves_semesters_without_a_graduation_target():
    from app.services.planning.generate import generate_plan
    program = inline([grp("major", {"id": "core", "type": "all", "allowReuse": False, "sourceRef": "s",
        "children": [crs("a", "MAJR 1001"), crs("b", "MAJR 2001")]})])
    plan = sample((1, "Fall", [{"kind": "course", "codes": ["MAJR 1001"]}]),
                  (2, "Spring", [{"kind": "course", "codes": ["MAJR 2001"]}]))
    result = generate_plan(program, coursework=[], metadata=metadata_for(program),
        terms=["Fall 2026", "Spring 2027", "Fall 2027", "Spring 2028"], credit_load=15, sample=plan)
    assert placed(result) == {"MAJR 1001": "Fall 2026", "MAJR 2001": "Spring 2028"}


def test_all_eight_sample_semesters_stay_in_their_published_order():
    from app.services.planning.generate import generate_plan
    codes = [f"SYN {1001 + i}" for i in range(8)]
    program = inline([grp("major", {"id": "core", "type": "all", "allowReuse": False, "sourceRef": "s",
        "children": [crs(f"r-{i}", code) for i, code in enumerate(codes)]})])
    terms = [f"{season} {year}" for year in range(2026, 2031) for season in ("Spring", "Fall")][1:9]
    plan = sample(*[(i // 2 + 1, "Fall" if i % 2 == 0 else "Spring", [{"kind": "course", "codes": [code]}]) for i, code in enumerate(codes)])
    result = generate_plan(program, coursework=[], metadata=metadata_for(program), terms=terms, credit_load=15,
        graduation="Spring 2030", sample=plan)
    assert placed(result) == dict(zip(codes, terms))


def test_registered_future_term_courses_use_up_that_terms_credit_load():
    rule = {"id": "core", "type": "all", "allowReuse": False, "sourceRef": "s",
            "children": [crs("a", "MAJR 1001"), crs("b", "MAJR 1002")]}
    program = inline([grp("major", rule)])
    registered = [done("REG 1001", 6, grade=None, term="Spring 2027", status="prog")]
    assert placed(generate(program, registered, load_limit=7)) == {"MAJR 1001": "Fall 2027", "MAJR 1002": "Fall 2027"}


# Liberal education gap filling.

def le_course(code, *designations, offered=("Fall", "Spring"), credits=3):
    return {"code": code, "designations": set(designations),
            "record": {"code": code, "title": code, "minimumCredits": credits, "maximumCredits": credits,
                       "offered": list(offered), "prerequisites": {"state": "verified_none", "expression": None}, "metadataWarnings": [], "blockedReason": None,
                       "metadataSource": "catalog"}}


def all_but(rules, *missing):
    names = {entry["designations"][0] for section in ("core", "themes") for entry in rules[section]["items"]}
    return frozenset(names - set(missing))


def filled(program, pool, *, coverage=frozenset(), designations=None, coursework=(), load_limit=15, terms=TERMS):
    from app.services.liberal_ed import load_rules
    from app.services.planning.generate import generate_plan
    return generate_plan(program, coursework=list(coursework), metadata=metadata_for(program), terms=terms,
                         credit_load=load_limit, le_coverage=coverage, le_pool=pool,
                         le_designations=designations or {}, le_rules=load_rules())


def four_wi():
    return [done(f"WRIT {3000 + i}W") for i in range(4)], {f"WRIT {3000 + i}W": {"Writing Intensive"} for i in range(4)}


def test_gaps_are_filled_preferring_courses_that_count_twice():
    from app.services.liberal_ed import load_rules
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    coursework, designations = four_wi()
    # Alphabetical order favors the single-purpose courses, so only the ranking picks ZZZ 1001.
    pool = [le_course("AAA 1001", "Race, Power, and Justice US"),
            le_course("ABC 1001", "Literature"),
            le_course("ZZZ 1001", "Literature", "Race, Power, and Justice US"),
            le_course("ART 1001", "Arts/Humanities")]
    coverage = all_but(load_rules(), "Literature", "Race, Power, and Justice US", "Arts/Humanities")
    result = filled(program, pool, coverage=coverage, designations=designations, coursework=coursework)
    slots = {item["code"]: item.get("slot") for item in result["placements"]}
    assert "AAA 1001" not in slots and "ABC 1001" not in slots
    assert slots["ZZZ 1001"] == "Race, Power, and Justice US, Literature"
    assert slots["ART 1001"] == "Arts/Humanities"


def test_major_courses_that_carry_a_designation_count_toward_it():
    from app.services.liberal_ed import load_rules
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    coursework, designations = four_wi()
    pool = [le_course("PHYS 1001", "Physical Sciences")]
    coverage = all_but(load_rules(), "Physical Sciences")
    result = filled(program, pool, coverage=coverage, designations={**designations, "MAJR 1001": {"Physical Sciences"}},
                    coursework=coursework)
    assert "PHYS 1001" not in placed(result)


def test_writing_intensive_courses_fill_the_total():
    from app.services.liberal_ed import load_rules
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    pool = [le_course(f"SYN 10{i}W", "Writing Intensive") for i in range(6)]
    result = filled(program, pool, coverage=all_but(load_rules()))
    assert sum(code.endswith("W") for code in placed(result)) == 4


def test_gap_filling_stops_cleanly_when_nothing_fits():
    from app.services.liberal_ed import load_rules
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    coursework, designations = four_wi()
    pool = [le_course("LIT 1001", "Literature", offered=("Summer",))]
    result = filled(program, pool, coverage=all_but(load_rules(), "Literature"), designations=designations, coursework=coursework)
    assert "LIT 1001" not in placed(result)
    assert "liberal_ed_unplanned" in result["warnings"]


def test_no_unplanned_warning_when_every_need_is_filled():
    from app.services.liberal_ed import load_rules
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    coursework, designations = four_wi()
    pool = [le_course("LIT 1001", "Literature")]
    result = filled(program, pool, coverage=all_but(load_rules(), "Literature"), designations=designations, coursework=coursework)
    assert "LIT 1001" in placed(result)
    assert "liberal_ed_unplanned" not in result["warnings"]


def test_no_rules_means_no_gap_filling():
    program = inline([grp("major", crs("a", "MAJR 1001"))])
    from app.services.planning.generate import generate_plan
    result = generate_plan(program, coursework=[], metadata=metadata_for(program), terms=TERMS, credit_load=15,
                           le_pool=[le_course("LIT 1001", "Literature")])
    assert placed(result) == {"MAJR 1001": "Spring 2027"}
