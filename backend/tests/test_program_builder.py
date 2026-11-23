"""Native catalog rules to v2 program files. Synthetic native records only; no network."""
import pytest

COURSES = {
    gid: {"course_group_id": gid, "revision_id": f"{gid}-2026-09-08", "code": code, "title": f"Title {code}",
          "credits_min": credits, "credits_max": credits, "typically_offered": offered, "prerequisite_text": prereq,
          "repeatable": "false", "effective_start_date": "2026-09-08", "effective_end_date": "",
          "source_url": f"https://umtc.catalog.prod.coursedog.com/courses/{gid}", "retrieved_at_utc": "2026-11-22T00:00:00Z"}
    for gid, code, credits, offered, prereq in [
        ("1", "TEST 1001", "4", "Every Fall & Spring", ""),
        ("2", "TEST 1002", "4", "Every Spring", "TEST 1001"),
        ("3", "TEST 1003", "3", "Periodic Fall", "TEST 1001 or TEST 1002"),
        ("4", "TEST 2001", "3", "", "[TEST 1001 or 1002] and TEST 1003"),
        ("5", "TEST 2002", "3", "Every Fall", "TEST 1001 or instr consent"),
        ("6", "TEST 2003", "", "Every Fall", ""),
    ]
}


def courses_rule(identity, groups, condition="completeVariableCoursesAndVariableCredits", **bounds):
    return {"condition": condition, "id": identity, "name": f"Rule {identity}",
            "value": {"condition": "courses", "id": f"v{identity}", "subSelections": [],
                      "values": [{"logic": logic, "value": ids} for logic, ids in groups]}, **bounds}


def native(rules, *, level="programRequirements", sections=None, notes=None, credits="120"):
    return {
        "program_id": "000001", "revision_id": "000001-2026-09-08", "name": "Synthetic Studies B.A.",
        "career": "Undergraduate", "program_type": "Major", "effective_start_date": "2026-09-08", "effective_end_date": "",
        "degree_credits_min": credits, "source_url": "https://umtc.catalog.prod.coursedog.com/programs/000001",
        "retrieved_at_utc": "2026-11-22T01:00:00+00:00",
        "requirements": {"requisitesSimple": sections or [
            {"id": "sec1", "name": "Major Requirements", "requirementLevel": level, "rules": rules}]},
        "requirement_levels": [{"key": "programRequirements", "notes": notes}] if notes else [],
    }


def build(record, overlay=None):
    from scripts.build_programs import build_program
    return build_program(record, COURSES, overlay=overlay)


def first_rule(program):
    return program["groups"][0]["rule"]


def test_builder_emits_a_valid_sourced_v2_program_with_term_from_the_revision_date():
    from app.schemas.programs import validate_program

    program = build(native([courses_rule("a", [("and", ["1"])], minCourses=1, minCredits=4)]))
    validate_program(program)
    assert (program["catalogTerm"], program["totalCredits"], program["name"]) == ("Fall 2026", 120, "Synthetic Studies B.A.")
    assert program["id"] == "synthetic-studies-ba"
    assert first_rule(program) == {"id": "r-a", "type": "course", "code": "TEST 1001", "sourceRef": "program", "label": "Rule a"}
    assert program["sources"]["program"]["url"] == "https://umtc.catalog.prod.coursedog.com/programs/000001"


@pytest.mark.parametrize("start,term", [("2026-09-08", "Fall 2026"), ("2027-01-19", "Spring 2027"), ("2027-09-07", "Fall 2027")])
def test_builder_maps_revision_start_dates_to_their_own_catalog_term(start, term):
    record = native([courses_rule("a", [("and", ["1"])])])
    record["effective_start_date"] = start
    assert build(record)["catalogTerm"] == term


def test_one_course_from_each_group_becomes_whole_sequence_with_credit_total():
    rule = first_rule(build(native([courses_rule("a", [("or", ["1", "2"]), ("and", ["3"])], minCourses=2, maxCourses=2, minCredits=7)])))
    assert rule["type"] == "all" and rule["allowReuse"] is True
    sequence, total = rule["children"]
    assert sequence["type"] == "all" and sequence["allowReuse"] is False
    assert [child["type"] for child in sequence["children"]] == ["any", "course"]
    assert (total["type"], total["minCredits"]) == ("credits", 7)


def test_pool_rule_keeps_credit_and_course_bounds_over_one_explicit_set():
    program = build(native([courses_rule("a", [("and", ["1"]), ("and", ["2"]), ("and", ["3"])], minCourses=1, maxCourses=1, minCredits=4)]))
    rule = first_rule(program)
    kinds = [(child["type"], child.get("minCredits"), child.get("minCourses"), child.get("maxCourses")) for child in rule["children"]]
    assert kinds == [("credits", 4, None, None), ("count", None, 1, None), ("count", None, None, 1)]
    assert program["courseSets"]["set-a"]["codes"] == ["TEST 1001", "TEST 1002", "TEST 1003"]


def test_all_and_groups_require_every_listed_course():
    rule = first_rule(build(native([courses_rule("a", [("and", ["1"]), ("and", ["2"])], condition="completedAllOf")])))
    assert rule["type"] == "all" and [child["code"] for child in rule["children"]] == ["TEST 1001", "TEST 1002"]


def test_nested_all_any_and_number_of_rules_preserve_alternatives():
    sub = [courses_rule(name, [("and", [gid])]) for name, gid in (("x", "1"), ("y", "2"), ("z", "3"))]
    program = build(native([{"condition": "allOf", "id": "outer", "name": "Outer", "subRules": [
        {"condition": "anyOf", "id": "choice", "name": "Choice", "subRules": sub[:2]},
        {"condition": "numberOf", "id": "two", "name": "Two of three", "number": 2, "subRules": sub}]}]))
    outer = first_rule(program)
    choice, two = outer["children"]
    assert choice["type"] == "any" and len(choice["children"]) == 2
    assert two["type"] == "any" and len(two["children"]) == 3
    assert all(branch["type"] == "all" and len(branch["children"]) == 2 for branch in two["children"])
    ids = []

    def walk(node):
        ids.append(node["id"])
        for child in node.get("children", []):
            walk(child)

    for group in program["groups"]:
        walk(group["rule"])
    assert len(ids) == len(set(ids))


def test_freeform_unknown_and_non_course_rules_become_review_instead_of_being_dropped():
    rules = [{"condition": "freeformText", "id": "f", "name": "Experience", "value": "Complete an international experience."},
             {"condition": "mystery", "id": "m", "name": "Mystery rule"},
             {"condition": "minimumCredits", "id": "attr", "name": "Attribute", "credits": 3,
              "value": {"condition": "courseAttributes", "values": []}}]
    rule = first_rule(build(native(rules)))
    assert [child["type"] for child in rule["children"]] == ["review", "review", "review"]
    assert "international experience" in rule["children"][0]["message"]


def test_unresolved_alternatives_remain_a_review_branch_and_unresolved_required_courses_review_the_rule():
    alternatives = first_rule(build(native([courses_rule("a", [("or", ["1", "missing"])], minCourses=1)])))
    assert alternatives["type"] == "any"
    assert [child["type"] for child in alternatives["children"]] == ["course", "review"]
    required = first_rule(build(native([courses_rule("b", [("and", ["1"]), ("and", ["missing"])], condition="completedAllOf")])))
    assert required["type"] == "review"


def test_courses_without_official_credits_are_never_given_guessed_metadata():
    program = build(native([courses_rule("a", [("or", ["1", "6"])], minCourses=1)]))
    assert "TEST 2003" not in program["courseMetadata"]
    assert [child["type"] for child in first_rule(program)["children"]] == ["course", "review"]


def test_supplemental_metadata_is_sourced_per_course_and_conservatively_parsed():
    program = build(native([courses_rule("a", [("and", [gid]) for gid in "12345"], minCourses=5)]))
    metadata = program["courseMetadata"]
    assert metadata["TEST 1001"]["prerequisites"] == {"expression": None, "sourceRef": "course-1"}
    assert metadata["TEST 1001"]["offered"] == ["Fall", "Spring"]
    assert metadata["TEST 1003"]["offered"] is None
    assert metadata["TEST 1002"]["prerequisites"]["expression"] == {"type": "course", "course_code": "TEST 1001"}
    assert metadata["TEST 2001"]["prerequisites"]["expression"] == {"type": "all_of", "requirements": [
        {"type": "any_of", "requirements": [{"type": "course", "course_code": "TEST 1001"}, {"type": "course", "course_code": "TEST 1002"}]},
        {"type": "course", "course_code": "TEST 1003"}]}
    assert metadata["TEST 2002"]["prerequisites"]["expression"] == {"type": "condition", "text": "TEST 1001 or instr consent"}
    assert program["sources"]["course-1"]["url"].endswith("/courses/1")


def test_prerequisite_parser_refuses_ambiguous_mixed_connectors():
    from scripts.build_programs import parse_prerequisites

    assert parse_prerequisites("TEST 1001 or TEST 1002 and TEST 1003") == {
        "type": "condition", "text": "TEST 1001 or TEST 1002 and TEST 1003"}
    assert parse_prerequisites("TEST 1001, TEST 1002") == {"type": "all_of", "requirements": [
        {"type": "course", "course_code": "TEST 1001"}, {"type": "course", "course_code": "TEST 1002"}]}


def test_sub_plans_and_section_notes_are_explicit_review_obligations():
    sections = [
        {"id": "sec1", "name": "Core", "requirementLevel": "programRequirements", "rules": [courses_rule("a", [("and", ["1"])])]},
        {"id": "sub", "name": "Track A", "requirementLevel": "programSubPlanRequirements", "rules": [courses_rule("b", [("and", ["2"])])]},
    ]
    program = build(native([], sections=sections, notes="<p>Complete the liberal education requirements.</p>"))
    labels = {group["label"]: group for group in program["groups"]}
    assert labels["Sub-plan requirements"]["rule"]["type"] == "review"
    assert "Track A" in labels["Sub-plan requirements"]["rule"]["message"]
    assert "liberal education" in labels["Additional program requirements"]["rule"]["message"]
    assert labels["Additional program requirements"]["category"] == "Liberal ed"


def test_programs_without_a_sourced_degree_total_are_skipped_with_a_reason():
    from scripts.build_programs import ProgramSkipped

    with pytest.raises(ProgramSkipped):
        build(native([courses_rule("a", [("and", ["1"])])], credits=""))


def test_overlay_replaces_named_groups_and_adds_sourced_policies_without_inventing_metadata():
    from app.schemas.programs import validate_program

    overlay = {
        "name": "Synthetic B.A.", "officialName": "Synthetic Studies B.A.",
        "sources": {"guide": {"url": "https://example.invalid/guide", "retrieved": "2026-11-22", "section": "Grades"}},
        "gradePolicy": {"minGrade": "C-", "allowS": False, "sourceRef": "guide"},
        "dropGroups": [], "replaceRules": {"r-a": {"id": "r-a", "type": "course", "code": "TEST 1002", "sourceRef": "guide"}},
        "courseSets": {}, "sharing": [], "adjustments": [],
    }
    program = validate_program(build(native([courses_rule("a", [("and", ["1"])])]), overlay=overlay))
    assert program["name"] == "Synthetic B.A." and program["officialName"] == "Synthetic Studies B.A."
    assert first_rule(program)["code"] == "TEST 1002"
    assert "TEST 1002" in program["courseMetadata"]
    assert all(group["gradePolicy"]["minGrade"] == "C-" for group in program["groups"])


def test_credit_cap_only_lists_are_review_rather_than_required_courses():
    rule = first_rule(build(native([courses_rule("cap", [("and", ["1"]), ("and", ["2"])], maxCredits=3)])))
    assert rule["type"] == "review"
    assert "at most 3 credits" in rule["message"]


def test_overlay_replacements_do_not_leave_orphan_course_sets():
    overlay = {"sources": {}, "replaceRules": {"r-a": {"id": "r-a", "type": "course", "code": "TEST 1001", "sourceRef": "program"}}}
    program = build(native([courses_rule("a", [("and", ["1"]), ("and", ["2"])], minCourses=1, minCredits=3)]), overlay=overlay)
    assert program["courseSets"] == {}
    assert set(program["courseMetadata"]) == {"TEST 1001"}


def test_prerequisite_text_none_is_a_verified_absence():
    from scripts.build_programs import parse_prerequisites
    assert parse_prerequisites("none") is None
    assert parse_prerequisites("None.") is None



def test_overlay_marks_named_rules_as_preferred():
    from app.schemas.programs import validate_program

    overlay = {"sources": {}, "preferredRules": ["r-a"]}
    program = validate_program(build(native([courses_rule("a", [("and", ["1"])])]), overlay=overlay))
    assert first_rule(program)["preferred"] is True


def test_overlay_preferred_courses_are_copied_to_the_program():
    from app.schemas.programs import validate_program

    program = validate_program(build(native([courses_rule("a", [("and", ["1"])])]), overlay={"sources": {}, "preferredCourses": ["TEST 1001"]}))
    assert program["preferredCourses"] == ["TEST 1001"]
