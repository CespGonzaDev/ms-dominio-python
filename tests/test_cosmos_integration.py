"""Pruebas de integración contra Cosmos DB real (emulador Docker o Azure).

Se omiten automáticamente si COSMOS_ENDPOINT / COSMOS_KEY no están definidos,
para no romper CI ni pruebas unitarias rápidas.
"""

import os

import pytest

from app.core.config import Settings, get_settings
from app.main import create_app
from app.repositories.cosmos_client import ensure_containers, get_database
from scripts.seed_cosmos import normalize_catalog, normalize_service

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "")
COSMOS_KEY = os.getenv("COSMOS_KEY", "")

pytestmark = pytest.mark.skipif(
    not (COSMOS_ENDPOINT and COSMOS_KEY),
    reason="Requiere COSMOS_ENDPOINT y COSMOS_KEY (ej. emulador local en Docker)",
)


@pytest.fixture(scope="module")
def cosmos_client():
    from fastapi.testclient import TestClient

    from app.repositories.cosmos_client import get_container

    get_database.cache_clear()
    ensure_containers()

    catalog = get_container("catalog")
    for doc in normalize_catalog([{"id": "it-area", "name": "IT Area"}], "area"):
        catalog.upsert_item(doc)
    for doc in normalize_catalog(
        [{"id": "it-py", "name": "IT Python", "areaId": "it-area"}], "skill"
    ):
        catalog.upsert_item(doc)

    services = get_container("services")
    seed_svc = normalize_service(
        {
            "id": "it-svc-1",
            "mentorId": "it-mentor-1",
            "mentor": {"id": "it-mentor-1", "name": "Mentor IT"},
            "title": "Integración Cosmos Python",
            "description": "Validación de filtros reales",
            "areaId": "it-area",
            "skillIds": ["it-py"],
            "type": "individual",
            "modality": "online",
            "platforms": ["zoom"],
            "durationMinutes": 60,
            "capacity": 1,
            "price": 0,
            "availableDays": ["monday"],
            "rating": 4.8,
            "reviewCount": 3,
        }
    )
    services.upsert_item(seed_svc)

    app = create_app()
    settings = Settings(
        _env_file=None,
        cosmos_endpoint=COSMOS_ENDPOINT,
        cosmos_key=COSMOS_KEY,
        cosmos_database=os.getenv("COSMOS_DATABASE", "skillgrow"),
        apim_cert_check=False,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_cosmos_catalog_and_search_filters(cosmos_client):
    h = {"X-User-Id": "it-user"}
    areas = cosmos_client.get("/v1/catalog/areas", headers=h).json()
    assert any(a["id"] == "it-area" for a in areas)
    assert any(
        s["id"] == "it-py"
        for s in cosmos_client.get("/v1/catalog/skills?areaId=it-area", headers=h).json()
    )

    for qs in (
        "search=integración",
        "skillId=it-py",
        "areaId=it-area",
        "modality=online",
        "type=individual",
        "minRating=4",
        "priceMax=10",
        "free=true",
        "day=monday",
        "sort=rating&page=1&pageSize=10",
    ):
        r = cosmos_client.get(f"/v1/services?{qs}", headers=h)
        assert r.status_code == 200, (qs, r.text)
        assert any(i["id"] == "it-svc-1" for i in r.json()["items"]), qs


def test_cosmos_service_crud_lifecycle(cosmos_client):
    h = {"X-User-Id": "it-owner", "X-User-Name": "Owner"}
    payload = {
        "title": "CRUD Cosmos Real",
        "description": "Prueba e2e",
        "areaId": "it-area",
        "skillIds": ["it-py"],
        "type": "individual",
        "modality": "online",
        "platforms": ["meet"],
        "durationMinutes": 30,
        "capacity": 1,
        "price": 25,
        "availableDays": ["friday"],
    }
    created = cosmos_client.post("/v1/services", json=payload, headers=h)
    assert created.status_code == 201, created.text
    sid = created.json()["id"]

    assert cosmos_client.get(f"/v1/services/{sid}", headers=h).status_code == 200
    assert any(s["id"] == sid for s in cosmos_client.get("/v1/me/services", headers=h).json())

    updated = cosmos_client.put(
        f"/v1/services/{sid}", json={**payload, "title": "CRUD Editado"}, headers=h
    )
    assert updated.status_code == 200 and updated.json()["title"] == "CRUD Editado"

    patched = cosmos_client.patch(
        f"/v1/services/{sid}/status", json={"status": "paused"}, headers=h
    )
    assert patched.status_code == 200 and patched.json()["status"] == "paused"

    deleted = cosmos_client.delete(f"/v1/services/{sid}", headers=h)
    assert deleted.status_code == 204
    assert cosmos_client.get(f"/v1/services/{sid}", headers=h).status_code == 404
