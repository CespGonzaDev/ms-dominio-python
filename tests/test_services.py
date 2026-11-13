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
    assert body["mentor"] == {"id": "alice", "name": "Alice", "avatar": "a.png"}
    assert body["status"] == "active"
    assert body["rating"] == 0 and body["reviewCount"] == 0
    assert isinstance(body["createdAtEpochMs"], int)
    assert body["createdAtEpochMs"] == body["updatedAtEpochMs"]


def test_create_ignores_mentor_sent_by_client(api, service_payload):
    body = _create(api, {**service_payload, "mentorId": "mallory", "rating": 5})
    assert body["mentorId"] == "alice"
    assert body["rating"] == 0


def test_create_invalid_returns_standard_error(api, service_payload):
    r = api.post("/v1/services", json={**service_payload, "price": -1}, headers=ALICE)
    assert r.status_code == 400
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(d["field"] == "price" for d in body["details"])
    assert body["path"] == "/v1/services"


def test_write_requires_identity(api, service_payload):
    assert api.post("/v1/services", json=service_payload).status_code == 401


def test_get_service_and_404(api, service_payload):
    created = _create(api, service_payload)
    assert api.get(f"/v1/services/{created['id']}", headers=BOB).json()["id"] == created["id"]
    r = api.get("/v1/services/nope", headers=BOB)
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_me_services_only_returns_mine(api, service_payload):
    _create(api, service_payload, ALICE)
    _create(api, service_payload, BOB)
    mine = api.get("/v1/me/services", headers=ALICE).json()
    assert len(mine) == 1 and mine[0]["mentorId"] == "alice"


def test_update_by_owner_keeps_server_fields(api, service_payload):
    created = _create(api, service_payload)
    r = api.put(
        f"/v1/services/{created['id']}",
        json={**service_payload, "title": "Nuevo título", "price": 0},
        headers=ALICE,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Nuevo título" and body["price"] == 0
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
    assert api.patch(url, json={"status": "paused"}, headers=ALICE).json()["status"] == "paused"
    assert api.patch(url, json={"status": "borrado"}, headers=ALICE).status_code == 400
    assert api.patch(url, json={"status": "active"}, headers=BOB).status_code == 403


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
        "/v1/services?search=%20Py%20&skillId=python&areaId=tech&modality=online"
        "&type=individual&minRating=4&priceMax=20&free=false&day=monday"
        "&sort=rating&page=2&pageSize=2",
        headers=BOB,
    )
    assert r.status_code == 200
    body = r.json()
    assert (body["totalRecords"], body["page"], body["pageSize"]) == (3, 2, 2)
    assert len(body["items"]) == 1
    f = service_repo.last_filters
    assert (f.search, f.skill_id, f.area_id, f.modality, f.type) == (
        "Py",
        "python",
        "tech",
        "online",
        "individual",
    )
    assert (f.min_rating, f.price_max, f.free, f.day, f.sort) == (4, 20, False, "monday", "rating")


def test_search_defaults(api, service_repo):
    assert api.get("/v1/services", headers=BOB).status_code == 200
    f = service_repo.last_filters
    assert (f.page, f.page_size, f.sort) == (1, 20, "recent")


def test_search_rejects_bad_params(api):
    for qs in ("sort=cualquiera", "pageSize=1000", "page=0", "minRating=9", "priceMax=-1"):
        r = api.get(f"/v1/services?{qs}", headers=BOB)
        assert r.status_code == 400, qs
        assert r.json()["code"] == "VALIDATION_ERROR"
