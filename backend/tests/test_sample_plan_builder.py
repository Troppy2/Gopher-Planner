"""Sample plan CSV rows -> per-program sample plan JSON. Synthetic rows only."""


def row(kind, *, code="", title="", credits="3", le="", year=1, season="Fall", plan="+ Synthetic BA", preferred="false",
        url="https://sampleplan.umn.edu/twin-cities/synthetic-ba"):
    return {"url": url, "program_title": "Synthetic B.A.", "plan": plan, "year": str(year), "season": season, "kind": kind,
            "code": code, "title": title, "credits": credits, "le": le, "preferred": preferred, "retrieved_at_utc": "2026-11-23"}


def test_le_categories_come_from_titles_and_abbreviations():
    from scripts.build_sample_plans import le_categories
    assert le_categories("Civic Life and Ethics, Historical Perspectives", "Civ, His") == [
        "Civic Life and Ethics", "Historical Perspectives"]
    assert le_categories("Arts/Humanities, Race, Power, and Justice US", "AH, RPJ") == [
        "Arts/Humanities", "Race, Power, and Justice US"]
    assert le_categories("", "SocS, Ltr") == ["Literature", "Social Sciences"]
    assert le_categories("Writing Intensive - Lower Division", "WI") == []  # WI is tracked by the major, not a slot


def test_rows_become_ordered_terms_with_courses_choices_slots_and_electives():
    from scripts.build_sample_plans import build_plan

    plan = build_plan([
        row("course", code="SYN 1001", title="Intro", credits="4", preferred="true"),
        row("le", title="Global Perspectives", le="GP"),
        row("choice", code="SYN 2001 or SYN 2002", credits="3-4", year=1, season="Spring"),
        row("elective", credits="3", year=2),
        row("other", title="SYN 1101 First Year Seminar", credits="1"),
        row("other", title="Course Title", credits="3"),
        row("course", code="SYN 9999", plan="+ Integrated Synthetic BA/MA"),
    ], program_id="synthetic-ba")
    assert plan["programId"] == "synthetic-ba" and plan["plan"] == "Synthetic BA"
    assert plan["source"] == "https://sampleplan.umn.edu/twin-cities/synthetic-ba"
    assert [(t["year"], t["season"]) for t in plan["terms"]] == [(1, "Fall"), (1, "Spring"), (2, "Fall")]
    fall = plan["terms"][0]["items"]
    assert fall == [
        {"kind": "course", "codes": ["SYN 1001"], "credits": 4.0, "preferred": True},
        {"kind": "le", "categories": ["Global Perspectives"], "credits": 3.0, "label": "Global Perspectives"},
        {"kind": "course", "codes": ["SYN 1101"], "credits": 1.0, "preferred": False},
    ]
    assert plan["terms"][1]["items"] == [{"kind": "choice", "codes": ["SYN 2001", "SYN 2002"], "credits": 3.0, "preferred": False}]
    assert plan["terms"][2]["items"] == [{"kind": "elective", "credits": 3.0}]


def test_matching_prefers_program_ids_then_names():
    from scripts.build_sample_plans import match_program
    programs = {"computer-science-bs": "Computer Science B.S.", "history-ba": "History B.A."}
    assert match_program("computer-science-bs-compsc", "Computer Science B.S. Comp.Sc.", programs) == "computer-science-bs"
    assert match_program("hist", "History B.A.", programs) == "history-ba"
    assert match_program("unknown-ba", "Unknown B.A.", programs) is None
