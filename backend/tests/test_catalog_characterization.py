import pytest


@pytest.mark.parametrize("query,codes", [
    ("subject=CSCI", [f"CSCI {1000 + i}" for i in range(1, 7)]),
    ("level=2", [f"MATH {2000 + i}" for i in range(7, 13)]),
    ("q=CSCI%201002", ["CSCI 1002"]),
    ("term=Fall&subject=CSCI", ["CSCI 1001", "CSCI 1003", "CSCI 1005"]),
    ("credits=3&subject=CSCI", ["CSCI 1002", "CSCI 1004", "CSCI 1006"]),
    ("requirement=synthetic-core", [f"CSCI {1000 + i}" for i in range(1, 7)]),
    ("availability=Offered%20next%20term&nextTerm=Spring&subject=CSCI", ["CSCI 1002", "CSCI 1004", "CSCI 1006"]),
])
def test_catalog_filters_return_only_matching_courses(client, catalog, make_user, login_as, query, codes):
    login_as(make_user())
    response = client.get("/api/v1/courses?" + query)
    assert response.status_code == 200
    assert [course["code"] for course in response.json["courses"]] == codes
    assert response.json["total"] == len(codes)


def test_catalog_pagination_keeps_total_and_stable_order(client, catalog, make_user, login_as):
    login_as(make_user())
    response = client.get("/api/v1/courses?limit=2&offset=5")
    assert response.status_code == 200
    assert [course["code"] for course in response.json["courses"]] == ["CSCI 1006", "MATH 2007"]
    assert (response.json["total"], response.json["limit"], response.json["offset"]) == (12, 2, 5)
