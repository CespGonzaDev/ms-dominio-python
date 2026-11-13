import uuid

from tests.conftest import ALICE, BOB


def _create(api, payload, headers=ALICE):
    r = api.post("/v1/services", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_sets_owner_and_epoch_fields(api, service_payload):
    body = _create(api, service_payload)
    assert uuid.UUID(body["id"]).version == 4
    assert body["mentorId"] == "alice"
    assert body["mentor"] == {
        "id": "alice",
        "fullName": "Alice",
        "avatarUrl": "a.png",
        "ratingAverage": 0.0,
        "ratingCount": 0,
    }
    assert body["area"] == {"id": "area_prog", "name": "Programación"}
    assert [s["id"] for s in body["skills"]] == ["sk_python"]
    assert body["status"] == "activo"
    assert body["availabilitySummary"] == "Lun, Mié"
    assert isinstance(body["createdAtEpochMs"], int)
    assert body["createdAtEpochMs"] == body["updatedAtEpochMs"]


def test_create_validates_catalog_ids_and_domain_rules(api, service_payload):
    bad_area = api.post("/v1/services", json={**service_payload, "areaId": "nope"}, headers=ALICE)
    assert bad_area.status_code == 400 and bad_area.json()["code"] == "INVALID_AREA"

    bad_skill = api.post(
        "/v1/services", json={**service_payload, "skillIds": ["nope"]}, headers=ALICE
    )
    assert bad_skill.status_code == 400 and bad_skill.json()["code"] == "INVALID_SKILL"

    bad_group = api.post(
        "/v1/services", json={**service_payload, "type": "grupal", "capacity": 1}, headers=ALICE
    )
    assert bad_group.status_code == 400 and bad_group.json()["code"] == "VALIDATION_ERROR"

    bad_virtual = api.post(
        "/v1/services", json={**service_payload, "platforms": []}, headers=ALICE
    )
    assert bad_virtual.status_code == 400


def test_create_ignores_mentor_sent_by_client(api, service_payload):
    body = _create(api, {**service_payload, "mentorId": "mallory", "status": "inactivo"})
    assert body["mentorId"] == "alice"
    assert body["status"] == "activo"


def test_create_invalid_returns_standard_error(api, service_payload):
    r = api.post("/v1/services", json={**service_payload, "price": -1}, headers=ALICE)
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["path"] == "/v1/services"


def test_write_requires_identity(api, service_payload):
    assert api.post("/v1/services", json=service_payload).status_code == 401


def test_get_service_and_404(api, service_payload):
    created = _create(api, service_payload)
    assert api.get(f"/v1/services/{created['id']}", headers=BOB).json()["id"] == created["id"]
    r = api.get("/v1/services/nope", headers=BOB)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_me_services_is_paginated_and_scoped(api, service_payload):
    _create(api, service_payload, ALICE)
    _create(api, service_payload, BOB)
    body = api.get("/v1/me/services", headers=ALICE).json()
    assert body["totalRecords"] == 1
    assert body["items"][0]["mentorId"] == "alice"


def test_update_by_owner_keeps_server_fields(api, service_payload):
    created = _create(api, service_payload)
    r = api.put(
        f"/v1/services/{created['id']}",
        json={**service_payload, "title": "Nuevo título", "price": None},
        headers=ALICE,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Nuevo título" and body["price"] is None
    assert body["mentorId"] == "alice"
    assert body["createdAtEpochMs"] == created["createdAtEpochMs"]
    assert body["updatedAtEpochMs"] >= created["updatedAtEpochMs"]


def test_update_by_non_owner_is_403(api, service_payload):
    created = _create(api, service_payload)
    r = api.put(f"/v1/services/{created['id']}", json=service_payload, headers=BOB)
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


def test_update_missing_is_404(api, service_payload):
    assert api.put("/v1/services/nope", json=service_payload, headers=ALICE).status_code == 404


def test_patch_status(api, service_payload):
    created = _create(api, service_payload)
    url = f"/v1/services/{created['id']}/status"
    assert api.patch(url, json={"status": "inactivo"}, headers=ALICE).json()["status"] == "inactivo"
    assert api.patch(url, json={"status": "borrado"}, headers=ALICE).status_code == 400
    assert api.patch(url, json={"status": "activo"}, headers=BOB).status_code == 403


def test_delete_flow(api, service_payload):
    created = _create(api, service_payload)
    url = f"/v1/services/{created['id']}"
    assert api.delete(url, headers=BOB).status_code == 403
    r = api.delete(url, headers=ALICE)
    assert r.status_code == 204 and r.content == b""
    assert api.get(url, headers=ALICE).status_code == 404
    assert api.delete(url, headers=ALICE).status_code == 404


def test_search_envelope_and_filter_parsing(api, service_payload, service_repo):
    for _ in range(3):
        _create(api, service_payload)
    r = api.get(
        "/v1/services?search=%20Py%20&skillId=sk_python&areaId=area_prog&mentorId=alice"
        "&modality=virtual&type=individual&minRating=4&priceMax=6000&free=false&day=1"
        "&sort=rating:desc&page=2&pageSize=2",
        headers=BOB,
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["totalRecords"], body["page"], body["pageSize"]) == (3, 2, 2)
    assert len(body["items"]) == 1
    f = service_repo.last_filters
    assert (f.search, f.skill_id, f.area_id, f.mentor_id, f.modality, f.type) == (
        "Py",
        "sk_python",
        "area_prog",
        "alice",
        "virtual",
        "individual",
    )
    assert (f.min_rating, f.price_max, f.free, f.day, f.sort) == (
        4,
        6000,
        False,
        1,
        "rating:desc",
    )


def test_search_defaults(api, service_repo):
    assert api.get("/v1/services", headers=BOB).status_code == 200
    f = service_repo.last_filters
    assert (f.page, f.page_size, f.sort) == (1, 10, "relevance")


def test_search_rejects_bad_params(api):
    for qs in ("sort=cualquiera", "pageSize=1000", "page=0", "minRating=9", "priceMax=-1", "day=9"):
        r = api.get(f"/v1/services?{qs}", headers=BOB)
        assert r.status_code == 400, qs
        assert r.json()["code"] == "VALIDATION_ERROR"
