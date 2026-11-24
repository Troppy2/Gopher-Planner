"""Liberal education tracker: core, themes, writing, APAS precedence. Synthetic courses only."""
import pytest

from app.services.liberal_ed import evaluate_liberal_ed, load_rules


@pytest.fixture
def rules():
    return load_rules()


def evaluate(rules, courses, designations, *, major_codes=(), major_subjects=(), audit=None):
    return evaluate_liberal_ed(rules, courses=courses, designations=designations,
                               major_codes=set(major_codes), major_subjects=set(major_subjects), audit=audit)


def item(section, identity):
    return next(entry for entry in section["items"] if entry["id"] == identity)


def done(code, term="Fall 2025"):
    return {"code": code, "status": "done", "term": term}


def test_rules_file_is_sourced_and_complete(rules):
    assert [entry["id"] for entry in rules["core"]["items"]] == [
        "arts-humanities", "biological-sciences", "historical-perspectives", "literature",
        "mathematical-thinking", "physical-sciences", "social-sciences"]
    assert rules["themes"]["required"] == 4 and len(rules["themes"]["items"]) == 5
    assert rules["themes"]["mandatory"] == ["race-power-justice"]
    for section in ("core", "themes", "writing"):
        assert rules[section]["sourceRef"] in rules["sources"]


def test_empty_record_needs_everything(rules):
    result = evaluate(rules, [], {})
    assert result["core"]["status"] == "short"
    assert {entry["status"] for entry in result["core"]["items"]} == {"needed"}
    assert result["themes"]["completed"] == 0 and result["themes"]["status"] == "short"
    assert result["writing"]["intensive"]["completed"] == {"total": 0, "upper": 0, "upperInMajor": 0}
    assert result["writing"]["firstYear"]["status"] == "needed"
    assert "Arts/Humanities" in result["remaining"] and "Writing Intensive" in result["remaining"]


def test_status_precedence_done_over_progress_over_planned(rules):
    courses = [done("HIST 1001"), {"code": "HIST 1002", "status": "prog", "term": "Fall 2026"},
               {"code": "BIOL 1001", "status": "prog", "term": "Fall 2026"},
               {"code": "LIT 1001", "status": "plan", "term": "Spring 2027"}]
    designations = {"HIST 1001": {"Historical Perspectives"}, "HIST 1002": {"Historical Perspectives"},
                    "BIOL 1001": {"Biological Sciences"}, "LIT 1001": {"Literature"}}
    core = evaluate(rules, courses, designations)["core"]
    history = item(core, "historical-perspectives")
    assert history["status"] == "done"
    assert history["codes"] == {"done": ["HIST 1001"], "prog": ["HIST 1002"], "plan": []}
    assert item(core, "biological-sciences")["status"] == "in_progress"
    assert item(core, "literature")["status"] == "planned"
    assert item(core, "arts-humanities")["status"] == "needed"


def test_core_met_and_on_track(rules):
    labels = [entry["designations"][0] for entry in rules["core"]["items"]]
    designations = {f"SYN {1000 + i}": {label} for i, label in enumerate(labels)}
    all_done = [done(code) for code in designations]
    assert evaluate(rules, all_done, designations)["core"]["status"] == "met"
    one_planned = all_done[:-1] + [{"code": "SYN 1006", "status": "plan", "term": "Fall 2027"}]
    assert evaluate(rules, one_planned, designations)["core"]["status"] == "on_track"


def test_themes_need_four_including_race_power_and_justice(rules):
    designations = {"SYN 1001": {"Civic Life and Ethics"}, "SYN 1002": {"Environment"},
                    "SYN 1003": {"Global Perspectives"}, "SYN 1004": {"Technology and Society"},
                    "SYN 1005": {"Race, Power, and Justice US"}}
    four_without_rpj = [done(code) for code in ("SYN 1001", "SYN 1002", "SYN 1003", "SYN 1004")]
    themes = evaluate(rules, four_without_rpj, designations)["themes"]
    assert themes["completed"] == 4 and themes["status"] == "short"
    assert themes["mandatoryMissing"] == ["race-power-justice"]
    three_and_rpj = [done(code) for code in ("SYN 1001", "SYN 1002", "SYN 1003", "SYN 1005")]
    assert evaluate(rules, three_and_rpj, designations)["themes"]["status"] == "met"
    planned_rpj = four_without_rpj[:3] + [{"code": "SYN 1005", "status": "plan", "term": "Fall 2027"}]
    themes = evaluate(rules, planned_rpj, designations)["themes"]
    assert (themes["completed"], themes["projected"], themes["status"]) == (3, 4, "on_track")


def test_former_diversity_designation_counts_for_race_power_and_justice(rules):
    result = evaluate(rules, [done("SYN 1001")], {"SYN 1001": {"Diversity and Soc Justice US"}})
    assert item(result["themes"], "race-power-justice")["status"] == "done"


def test_one_course_counts_for_a_core_a_theme_and_writing(rules):
    designations = {"SYN 3001W": {"Literature", "Race, Power, and Justice US", "Writing Intensive"}}
    result = evaluate(rules, [done("SYN 3001W")], designations)
    assert item(result["core"], "literature")["status"] == "done"
    assert item(result["themes"], "race-power-justice")["status"] == "done"
    assert result["writing"]["intensive"]["completed"]["total"] == 1


def test_writing_intensive_counts_upper_division_and_major(rules):
    designations = {code: {"Writing Intensive"} for code in ("SYN 1001W", "SYN 3001W", "CSCI 3921W", "CSCI 4511W")}
    courses = [done("SYN 1001W"), done("SYN 3001W"), done("CSCI 3921W"),
               {"code": "CSCI 4511W", "status": "plan", "term": "Spring 2027"}]
    intensive = evaluate(rules, courses, designations, major_subjects={"CSCI"})["writing"]["intensive"]
    assert intensive["completed"] == {"total": 3, "upper": 2, "upperInMajor": 1}
    assert intensive["projected"] == {"total": 4, "upper": 3, "upperInMajor": 2}
    assert intensive["status"] == "on_track"
    assert intensive["codes"]["plan"] == ["CSCI 4511W"]


def test_writing_intensive_needs_an_upper_division_course_in_the_major(rules):
    designations = {code: {"Writing Intensive"} for code in ("SYN 1001W", "SYN 1002W", "SYN 3001W", "SYN 3002W")}
    courses = [done(code) for code in designations]
    intensive = evaluate(rules, courses, designations, major_subjects={"CSCI"})["writing"]["intensive"]
    assert intensive["completed"]["total"] == 4 and intensive["status"] == "short"
    # A program's own listed course is in the major even when its subject differs.
    intensive = evaluate(rules, courses, designations, major_codes={"SYN 3002W"})["writing"]["intensive"]
    assert intensive["status"] == "met"


def test_first_year_writing_from_coursework(rules):
    first = evaluate(rules, [{"code": "WRIT 1301", "status": "prog", "term": "Fall 2026"}], {})["writing"]["firstYear"]
    assert first == {**first, "status": "in_progress", "codes": {"done": [], "prog": ["WRIT 1301"], "plan": []}}


def test_apas_covered_category_counts_without_a_course(rules):
    result = evaluate(rules, [], {}, audit=({"Arts/Humanities", "Literature"}, {"Literature"}))
    entry = item(result["core"], "literature")
    assert entry["status"] == "done" and entry["source"] == "apas"


def test_apas_omitted_core_category_is_not_required(rules):
    required = {entry["designations"][0] for entry in rules["core"]["items"]} - {"Biological Sciences"}
    result = evaluate(rules, [], {}, audit=(required, set()))
    assert item(result["core"], "biological-sciences")["status"] == "not_required"
    assert "Biological Sciences" not in result["remaining"]


def test_apas_without_theme_headings_does_not_waive_themes(rules):
    result = evaluate(rules, [], {}, audit=({"Literature"}, set()))
    assert {entry["status"] for entry in result["themes"]["items"]} == {"needed"}


def test_catalog_done_but_apas_not_covered_needs_review(rules):
    result = evaluate(rules, [done("LIT 1001")], {"LIT 1001": {"Literature"}},
                      audit=({"Literature", "Arts/Humanities"}, set()))
    entry = item(result["core"], "literature")
    assert entry["status"] == "needs_review"
    assert result["core"]["status"] == "needs_review"


def test_remaining_lists_only_unplanned_needs(rules):
    designations = {"SYN 1001": {"Literature"}, "SYN 1002": {"Global Perspectives"}}
    courses = [done("SYN 1001"), {"code": "SYN 1002", "status": "plan", "term": "Fall 2027"}]
    remaining = evaluate(rules, courses, designations)["remaining"]
    assert "Literature" not in remaining and "Global Perspectives" not in remaining
    assert "Race, Power, and Justice US" in remaining and "Diversity and Soc Justice US" not in remaining


def test_themes_drop_out_of_remaining_once_projected_complete(rules):
    designations = {"SYN 1001": {"Civic Life and Ethics"}, "SYN 1002": {"Environment"},
                    "SYN 1003": {"Global Perspectives"}, "SYN 1005": {"Race, Power, and Justice US"}}
    remaining = evaluate(rules, [done(code) for code in designations], designations)["remaining"]
    assert "Technology and Society" not in remaining


# open_needs: what a generator should still fill.

def needs(rules, covered=(), wi=0):
    from app.services.liberal_ed import open_needs
    return [label for label, _ in open_needs(rules, set(covered), wi)]


def all_core(rules):
    return {entry["designations"][0] for entry in rules["core"]["items"]}


def test_open_needs_lists_race_power_justice_first_then_core_then_themes_then_writing(rules):
    result = needs(rules)
    assert result[0] == "Race, Power, and Justice US"
    assert result[1:8] == [entry["designations"][0] for entry in rules["core"]["items"]]
    assert result[-1] == "Writing Intensive"


def test_open_needs_stops_asking_for_themes_once_four_including_rpj_are_covered(rules):
    covered = all_core(rules) | {"Race, Power, and Justice US", "Civic Life and Ethics", "Environment", "Global Perspectives"}
    assert needs(rules, covered, wi=4) == []


def test_open_needs_still_requires_rpj_when_four_other_themes_are_covered(rules):
    covered = all_core(rules) | {"Civic Life and Ethics", "Environment", "Global Perspectives", "Technology and Society"}
    assert needs(rules, covered, wi=4) == ["Race, Power, and Justice US"]


def test_open_needs_accepts_the_former_diversity_name(rules):
    covered = all_core(rules) | {"Diversity and Soc Justice US", "Civic Life and Ethics", "Environment", "Global Perspectives"}
    assert needs(rules, covered, wi=4) == []


def test_open_needs_counts_writing_intensive_total(rules):
    covered = all_core(rules) | {"Race, Power, and Justice US", "Civic Life and Ethics", "Environment", "Global Perspectives"}
    assert needs(rules, covered, wi=3) == ["Writing Intensive"]
