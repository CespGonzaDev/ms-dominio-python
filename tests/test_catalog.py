from tests.conftest import ALICE


def test_areas_and_skills(api, catalog_repo):
    catalog_repo.docs = [
        {"id": "tech", "type": "area", "name": "Tecnología", "icon": "cpu"},
        {"id": "python", "type": "skill", "name": "Python", "areaId": "tech"},
        {"id": "cook", "type": "skill", "name": "Cocina", "areaId": "food"},
    ]
    areas = api.get("/v1/catalog/areas", headers=ALICE)
    assert areas.status_code == 200
    assert areas.json() == [{"id": "tech", "name": "Tecnología", "type": "area", "icon": "cpu"}]

    skills = api.get("/v1/catalog/skills", headers=ALICE).json()
    assert {s["id"] for s in skills} == {"python", "cook"}
    assert skills[0]["areaId"] in {"tech", "food"}

    filtered = api.get("/v1/catalog/skills?areaId=tech", headers=ALICE).json()
    assert [s["id"] for s in filtered] == ["python"]


def test_catalog_requires_identity(api):
    r = api.get("/v1/catalog/areas")
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"
