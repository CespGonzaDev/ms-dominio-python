from tests.conftest import ALICE


def test_areas_and_skills(api, catalog_repo):
    areas = api.get("/v1/catalog/areas", headers=ALICE)
    assert areas.status_code == 200
    assert {a["id"] for a in areas.json()} == {"area_prog", "area_idi"}

    skills = api.get("/v1/catalog/skills", headers=ALICE).json()
    assert {s["id"] for s in skills} == {"sk_python", "sk_sql", "sk_ingles"}

    filtered = api.get("/v1/catalog/skills?areaId=area_prog", headers=ALICE).json()
    assert {s["id"] for s in filtered} == {"sk_python", "sk_sql"}

    searched = api.get("/v1/catalog/skills?search=pyt", headers=ALICE).json()
    assert [s["id"] for s in searched] == ["sk_python"]


def test_catalog_and_services_are_public_without_identity(api):
    assert api.get("/v1/catalog/areas").status_code == 200
    assert api.get("/v1/catalog/skills").status_code == 200
    assert api.get("/v1/services").status_code == 200
