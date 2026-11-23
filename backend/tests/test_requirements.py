"""Pure requirement evaluation. Synthetic programs only; no Flask app or database."""
import copy
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "programs"


def rich():
    return json.loads((FIXTURES / "rich-synthetic--fall-2026.json").read_text(encoding="utf-8"))


def attempt(code, grade="A", status="done", credits=3, term="Fall 2025"):
    return {"code": code, "grade": grade, "status": status, "credits": credits, "term": term}


def evaluate(program, attempts):
    from app.services.requirements import evaluate_program
    return evaluate_program(program, attempts)


def entry(result, identity):
    return next(item for item in result["requirementProgress"] if item["id"] == identity)


def make_program(groups, *, sets=None, sharing=None, adjustments=None):
    from app.schemas.programs import validate_program

    codes = set()

    def walk(rule):
        if rule["type"] == "course":
            codes.add(rule["code"])
        for child in rule.get("children", []):
            walk(child)

    for item in groups:
        walk(item["rule"])
    for course_set in (sets or {}).values():
        codes.update(course_set["codes"])
    program = {
        "schemaVersion": 2, "id": "inline", "name": "Inline B.S.", "officialProgramId": "inline",
        "catalogTerm": "Fall 2026", "totalCredits": 12, "source": "Synthetic",
        "sources": {"s": {"url": "https://example.invalid", "retrieved": "2026-11-22", "section": "Synthetic"}},
        "courseSets": sets or {}, "groups": groups, "sharing": sharing or [], "adjustments": adjustments or [],
        "courseMetadata": {code: {"catalogTerm": "Fall 2026", "title": code, "minimumCredits": 3, "maximumCredits": 3,
                                  "offered": None, "prerequisites": None, "sourceRef": "s"} for code in codes},
    }
    return validate_program(program)


POLICY = {"minGrade": "C-", "allowS": False, "sourceRef": "s"}


def group(identity, rule, policy=POLICY):
    value = {"id": identity, "label": identity, "category": "Major core", "sourceRef": "s", "rule": rule}
    if policy:
        value["gradePolicy"] = policy
    return value


def course(identity, code):
    return {"id": identity, "type": "course", "code": code, "sourceRef": "s"}


def test_every_requirement_node_reports_completed_and_projected_progress():
    import importlib.util

    assert importlib.util.find_spec("app.services.requirements") is not None, "Missing requirement evaluator"
    result = evaluate(rich(), [])
    ids = [item["id"] for item in result["requirementProgress"]]
    assert ids[:5] == ["core", "intro-options", "sequence-a", "a1", "a2"]
    assert {"math", "calc", "placement", "electives", "elective-total", "capped-topics", "libed", "libed-review"} <= set(ids)
    for item in result["requirementProgress"]:
        assert {"id", "label", "completedStatus", "projectedStatus", "completedEvidence", "projectedEvidence", "details"} <= set(item)
        for evidence in (item["completedEvidence"], item["projectedEvidence"]):
            assert {"matchedCodes", "missingCodes", "appliedAdjustments"} <= set(evidence)
    assert entry(result, "a1")["label"] == "TEST 1001"
    assert entry(result, "intro-options")["label"] == "Synthetic core"


def test_empty_coursework_leaves_course_rules_unsatisfied_and_review_rules_unresolved():
    result = evaluate(rich(), [])
    assert entry(result, "core")["completedStatus"] == "unsatisfied"
    assert entry(result, "libed")["completedStatus"] == "needs_review"
    assert entry(result, "math")["completedStatus"] == "unsatisfied"
    assert "Synthetic placement requirement" in entry(result, "math")["details"]
    assert entry(result, "capped-topics")["completedStatus"] == "satisfied"
    assert set(result["warnings"]) == {"requirements_incomplete", "requirements_need_review"}


def test_a_complete_nested_sequence_satisfies_its_alternative():
    result = evaluate(rich(), [attempt("TEST 1001"), attempt("TEST 1002", "B")])
    assert entry(result, "sequence-a")["completedStatus"] == "satisfied"
    assert entry(result, "core")["completedStatus"] == "satisfied"
    assert entry(result, "core")["completedEvidence"]["matchedCodes"] == ["TEST 1001", "TEST 1002"]


def test_incomplete_halves_do_not_qualify_and_missing_codes_follow_the_chosen_branch():
    result = evaluate(rich(), [attempt("TEST 1001")])
    assert entry(result, "intro-options")["completedStatus"] == "unsatisfied"
    assert entry(result, "intro-options")["completedEvidence"]["missingCodes"] == ["TEST 1002"]
    assert "TEST 1003" not in entry(result, "core")["completedEvidence"]["missingCodes"]


@pytest.mark.parametrize("grade,status", [("C-", "satisfied"), ("D", "unsatisfied"), ("F", "unsatisfied"),
                                          ("S", "unsatisfied"), ("W", "unsatisfied"), (None, "needs_review")])
def test_grade_thresholds_use_explicit_grade_ordering(grade, status):
    result = evaluate(rich(), [attempt("TEST 1003", grade, credits=4)])
    assert entry(result, "sequence-b")["completedStatus"] == status


def test_s_grade_counts_only_where_the_sourced_policy_allows_it():
    result = evaluate(rich(), [attempt("TEST 3001", "S"), attempt("TEST 3002", "S"), attempt("MATH 3001", "S")])
    assert entry(result, "electives")["completedStatus"] == "satisfied"


def test_in_progress_and_planned_courses_satisfy_only_the_projected_evaluation():
    result = evaluate(rich(), [attempt("TEST 1003", None, "prog", 4), attempt("TEST 1001", None, "plan")])
    item = entry(result, "sequence-b")
    assert (item["completedStatus"], item["projectedStatus"]) == ("unsatisfied", "satisfied")
    assert any("C-" in detail for detail in item["details"])
    assert entry(result, "core")["projectedEvidence"]["matchedCodes"] == ["TEST 1003"]


def test_repeated_attempts_use_the_best_qualifying_attempt_once():
    result = evaluate(rich(), [attempt("TEST 1003", "F", credits=4, term="Fall 2025"),
                               attempt("TEST 1003", "B", credits=4, term="Spring 2026"),
                               attempt("TEST 3001", "A", term="Fall 2025"), attempt("TEST 3001", "B", term="Spring 2026")])
    assert entry(result, "sequence-b")["completedStatus"] == "satisfied"
    assert entry(result, "elective-total")["completedEvidence"]["matchedCredits"] == 3


def test_combined_elective_total_counts_unique_evidence_with_subject_minimum_and_math_inside_it():
    result = evaluate(rich(), [attempt("TEST 3001"), attempt("TEST 3002"), attempt("MATH 3001")])
    total = entry(result, "elective-total")["completedEvidence"]
    assert (total["requiredCredits"], total["matchedCredits"]) == (9, 9)
    assert entry(result, "test-minimum")["completedEvidence"]["matchedCredits"] == 6
    assert entry(result, "math-elective")["completedEvidence"]["matchedCourses"] == 1
    assert entry(result, "electives")["completedStatus"] == "satisfied"
    assert sorted(entry(result, "electives")["completedEvidence"]["matchedCodes"]) == ["MATH 3001", "TEST 3001", "TEST 3002"]


def test_unmet_subject_minimum_keeps_the_combined_group_unsatisfied():
    result = evaluate(rich(), [attempt("TEST 3001"), attempt("MATH 3001"), attempt("MATH 3001", term="Spring 2026")])
    assert entry(result, "test-minimum")["completedStatus"] == "unsatisfied"
    assert entry(result, "electives")["completedStatus"] == "unsatisfied"


def test_maximum_course_cap_limits_the_whole_group_pool():
    result = evaluate(rich(), [attempt("TEST 3900"), attempt("TEST 3901"), attempt("MATH 3001")])
    assert entry(result, "elective-total")["completedEvidence"]["matchedCredits"] == 6
    assert entry(result, "capped-topics")["completedEvidence"]["matchedCourses"] == 1
    assert entry(result, "electives")["completedStatus"] == "unsatisfied"


def test_reuse_inside_an_all_rule_requires_explicit_permission():
    sets = {"pool": {"codes": ["TEST 1001", "TEST 1002"], "sourceRef": "s"}}
    rule = {"id": "both", "type": "all", "allowReuse": False, "sourceRef": "s", "children": [
        course("one", "TEST 1001"),
        {"id": "pool-credits", "type": "credits", "courseSet": "pool", "minCredits": 3, "sourceRef": "s"}]}
    prohibited = make_program([group("g", rule)], sets=sets)
    assert entry(evaluate(prohibited, [attempt("TEST 1001")]), "g")["completedStatus"] == "unsatisfied"
    permitted = make_program([group("g", {**rule, "allowReuse": True})], sets=sets)
    assert entry(evaluate(permitted, [attempt("TEST 1001")]), "g")["completedStatus"] == "satisfied"


def three_groups(sharing):
    return make_program([group(name, course(f"{name}-x", "TEST 1001")) for name in ("a", "b", "c")], sharing=sharing)


def test_top_level_groups_never_share_evidence_without_a_declaration():
    result = evaluate(three_groups([]), [attempt("TEST 1001")])
    assert [entry(result, name)["completedStatus"] for name in "abc"] == ["satisfied", "unsatisfied", "unsatisfied"]


def test_sharing_declarations_are_not_transitive():
    result = evaluate(three_groups([{"groups": ["a", "b"], "sourceRef": "s"}, {"groups": ["b", "c"], "sourceRef": "s"}]),
                      [attempt("TEST 1001")])
    assert [entry(result, name)["completedStatus"] for name in "abc"] == ["satisfied", "satisfied", "unsatisfied"]
    joint = evaluate(three_groups([{"groups": ["a", "b", "c"], "sourceRef": "s"}]), [attempt("TEST 1001")])
    assert [entry(joint, name)["completedStatus"] for name in "abc"] == ["satisfied"] * 3


def test_sourced_substitution_reduces_the_target_once_and_reports_it():
    courses = [attempt("TEST 3001"), attempt("TEST 3002")]
    without = entry(evaluate(rich(), courses), "elective-total")
    assert (without["completedStatus"], without["completedEvidence"]["requiredCredits"]) == ("unsatisfied", 9)
    waived = evaluate(rich(), [*courses, attempt("TEST 1003", credits=4), attempt("TEST 1003", "B", credits=4, term="Spring 2026")])
    item = entry(waived, "elective-total")
    assert item["completedStatus"] == "satisfied"
    assert item["completedEvidence"]["requiredCredits"] == 6
    assert item["completedEvidence"]["appliedAdjustments"] == ["substitution-waiver"]


def test_adjustments_apply_separately_to_completed_and_projected_evaluations():
    result = evaluate(rich(), [attempt("TEST 3001"), attempt("TEST 3002"), attempt("TEST 1003", None, "plan", 4)])
    item = entry(result, "elective-total")
    assert item["completedEvidence"]["appliedAdjustments"] == []
    assert item["projectedEvidence"]["appliedAdjustments"] == ["substitution-waiver"]
    assert (item["completedStatus"], item["projectedStatus"]) == ("unsatisfied", "satisfied")


def test_a_sourced_waiver_satisfies_its_target_and_explains_the_qualifying_course():
    program = make_program([group("route", course("route-course", "TEST 1001")), group("waived", course("waived-course", "TEST 2001"))],
                           adjustments=[{"id": "waive", "sourceRef": "s", "whenAnySatisfied": ["route-course"],
                                         "effects": [{"targetId": "waived-course", "satisfy": True}]}])
    item = entry(evaluate(program, [attempt("TEST 1001")]), "waived-course")
    assert item["completedStatus"] == "satisfied"
    assert item["completedEvidence"]["appliedAdjustments"] == ["waive"]
    assert any("TEST 1001" in detail for detail in item["details"])
    assert item["completedEvidence"]["matchedCodes"] == []


def test_review_rules_are_never_silently_satisfied():
    result = evaluate(rich(), [attempt(code) for code in ("TEST 1001", "TEST 1002", "MATH 1001", "TEST 3001", "TEST 3002", "MATH 3001")])
    assert entry(result, "math")["completedStatus"] == "needs_review"
    assert entry(result, "libed")["projectedStatus"] == "needs_review"
    assert result["warnings"] == ["requirements_need_review"]


def test_missing_grade_policy_is_a_review_gap_rather_than_an_invented_threshold():
    program = make_program([group("g", course("c", "TEST 1001"), policy=None)])
    item = entry(evaluate(program, [attempt("TEST 1001", "A")]), "c")
    assert item["completedStatus"] == "needs_review"
    assert any("grade" in detail.lower() for detail in item["details"])


def test_any_rule_without_a_satisfied_branch_reports_review_when_a_branch_is_unresolved():
    rule = {"id": "choice", "type": "any", "sourceRef": "s", "children": [
        course("first", "TEST 1001"), {"id": "other", "type": "review", "message": "Advisor approval", "sourceRef": "s"}]}
    result = evaluate(make_program([group("g", rule)]), [])
    assert entry(result, "choice")["completedStatus"] == "needs_review"


def test_evaluation_is_deterministic_and_does_not_mutate_inputs():
    program, courses = rich(), [attempt("TEST 1001"), attempt("TEST 3001", "S")]
    snapshot = copy.deepcopy((program, courses))
    assert evaluate(program, courses) == evaluate(program, courses)
    assert (program, courses) == snapshot


def test_evidence_in_an_incomplete_alternative_remains_available_to_later_groups():
    pair = {"id": "pair", "type": "all", "allowReuse": False, "sourceRef": "s",
            "children": [course("pair-a", "TEST 1001"), course("pair-b", "TEST 1002")]}
    choice = {"id": "choice", "type": "any", "sourceRef": "s", "children": [course("alone", "TEST 1003"), pair]}
    program = make_program([group("first", choice), group("second", course("later", "TEST 1002"))])
    result = evaluate(program, [attempt("TEST 1002")])
    assert entry(result, "first")["completedStatus"] == "unsatisfied"
    assert entry(result, "second")["completedStatus"] == "satisfied"


def test_unresolved_evidence_too_small_for_a_quota_leaves_it_unsatisfied():
    sets = {"pool": {"codes": ["TEST 1001", "TEST 1002", "TEST 1003"], "sourceRef": "s"}}
    rule = {"id": "quota", "type": "credits", "courseSet": "pool", "minCredits": 6, "sourceRef": "s"}
    count = {"id": "two", "type": "count", "courseSet": "pool", "minCourses": 2, "sourceRef": "s"}
    program = make_program([group("g", rule, policy=None), group("h", count, policy=None)], sets=sets,
                           sharing=[{"groups": ["g", "h"], "sourceRef": "s"}])
    one = evaluate(program, [attempt("TEST 1001")])
    assert (entry(one, "quota")["completedStatus"], entry(one, "two")["completedStatus"]) == ("unsatisfied", "unsatisfied")
    two = evaluate(program, [attempt("TEST 1001"), attempt("TEST 1002")])
    assert (entry(two, "quota")["completedStatus"], entry(two, "two")["completedStatus"]) == ("needs_review", "needs_review")
