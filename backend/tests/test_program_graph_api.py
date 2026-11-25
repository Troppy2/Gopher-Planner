"""Program prerequisite graph for the flow chart: GET /programs/<id>/graph."""
import copy
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "programs"


def graph(client, program_id="rich-synthetic", **params):
    return client.get(f"/api/v1/programs/{program_id}/graph", query_string=params)


def test_graph_requires_authentication(client, program_files):
    assert graph(client).status_code == 401


def test_graph_lists_every_referenced_course_once(client, make_user, login_as, program_files):
    login_as(make_user())
    response = graph(client)
    assert response.status_code == 200
    codes = [node["code"] for node in response.json["nodes"]]
    assert codes == ["MATH 1001", "MATH 3001", "TEST 1001", "TEST 1002", "TEST 1003",
                     "TEST 3001", "TEST 3002", "TEST 3003", "TEST 3900", "TEST 3901"]
    assert response.json["program"] == {"id": "rich-synthetic", "name": "Rich Synthetic B.S.",
                                        "catalogTerm": "Fall 2026", "reviewed": False}


def test_graph_edges_follow_prerequisites_and_mark_alternatives(client, make_user, login_as, program_files):
    login_as(make_user())
    edges = graph(client).json["edges"]
    assert edges == [
        {"source": "MATH 1001", "target": "MATH 3001", "alternative": False},
        {"source": "TEST 1001", "target": "TEST 1002", "alternative": False},
        {"source": "TEST 1002", "target": "TEST 3001", "alternative": False},
        {"source": "TEST 1002", "target": "TEST 3002", "alternative": True},
        {"source": "TEST 1003", "target": "TEST 3002", "alternative": True},
    ]


def test_graph_nodes_carry_groups_and_prerequisite_state(client, make_user, login_as, program_files):
    login_as(make_user())
    nodes = {node["code"]: node for node in graph(client).json["nodes"]}
    assert [group["id"] for group in nodes["TEST 1001"]["groups"]] == ["core"]
    assert nodes["TEST 1002"]["prerequisiteState"] == "tree"
    assert nodes["TEST 1001"]["prerequisiteState"] == "verified_none"
    # Missing prerequisite metadata is reported as unknown, never as "no prerequisites".
    assert nodes["TEST 3003"]["prerequisiteState"] == "unknown"
    assert "course_metadata_unavailable" in nodes["TEST 3003"]["metadataWarnings"]
    assert "prerequisites_require_review" in nodes["TEST 3900"]["metadataWarnings"]
    assert nodes["TEST 1002"]["title"]
    assert nodes["TEST 1002"]["metadataSource"] == "program"


def test_unknown_program_is_404(client, make_user, login_as, program_files):
    login_as(make_user())
    response = graph(client, "not-a-program")
    assert response.status_code == 404
    assert response.json["code"] == "unknown_program"


def test_unknown_catalog_term_is_404(client, make_user, login_as, program_files):
    login_as(make_user())
    response = graph(client, catalogTerm="Fall 2030")
    assert response.status_code == 404
    assert response.json["code"] == "catalog_term_unavailable"


@pytest.fixture
def custom_programs(tmp_path, monkeypatch):
    """Copy the rich fixture into a temporary directory so a test can add versions or edges."""
    from app.services import programs

    def write(*variants):
        for variant in variants:
            (tmp_path / f"{variant['id']}--{variant['catalogTerm'].lower().replace(' ', '-')}.json").write_text(
                json.dumps(variant), encoding="utf-8")
        monkeypatch.setenv("PROGRAM_DATA_PATH", str(tmp_path))
        programs.clear_program_cache()

    yield write, json.loads((FIXTURES / "rich-synthetic--fall-2026.json").read_text(encoding="utf-8"))
    programs.clear_program_cache()


def test_two_versions_require_a_catalog_term(client, make_user, login_as, custom_programs):
    write, base = custom_programs
    later = copy.deepcopy(base)
    later["catalogTerm"] = "Fall 2027"
    for record in later["courseMetadata"].values():
        if isinstance(record, dict) and "catalogTerm" in record:
            record["catalogTerm"] = "Fall 2027"
    for mapping in later.get("catalogCompatibility", []):
        mapping["catalogTerm"] = "Fall 2027"
    write(base, later)
    login_as(make_user())
    response = graph(client)
    assert response.status_code == 400
    assert response.json["code"] == "catalog_term_required"
    assert graph(client, catalogTerm="Fall 2027").json["program"]["catalogTerm"] == "Fall 2027"


def test_prerequisites_outside_the_program_are_listed_not_linked(client, make_user, login_as, custom_programs):
    write, base = custom_programs
    base["courseMetadata"]["TEST 1001"]["prerequisites"] = {
        "expression": {"type": "course", "course_code": "PREP 0999"}, "sourceRef": "synthetic"}
    write(base)
    login_as(make_user())
    body = graph(client).json
    node = next(node for node in body["nodes"] if node["code"] == "TEST 1001")
    assert node["outsidePrerequisites"] == ["PREP 0999"]
    assert all("PREP 0999" not in (edge["source"], edge["target"]) for edge in body["edges"])
    assert "PREP 0999" not in [node["code"] for node in body["nodes"]]


def test_program_listing_includes_the_graph_id(client, make_user, login_as, program_files):
    login_as(make_user())
    listed = {item["name"]: item["id"] for item in client.get("/api/v1/programs").json["programs"]}
    assert listed["Rich Synthetic B.S."] == "rich-synthetic"
