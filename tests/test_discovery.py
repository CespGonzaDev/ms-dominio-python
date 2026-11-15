from tests.conftest import ALICE, BOB


def _seed_two_mentors(api, service_payload):
    r1 = api.post("/v1/services", json=service_payload, headers=ALICE)
    assert r1.status_code == 201
    r2 = api.post(
        "/v1/services",
        json={
            **service_payload,
            "title": "Inglés conversacional",
            "areaId": "area_idi",
            "skillIds": ["sk_ingles"],
        },
        headers=BOB,
    )
    assert r2.status_code == 201


def test_mentors_listing_and_filters(api, service_payload):
    _seed_two_mentors(api, service_payload)
    all_mentors = api.get("/v1/mentors", headers=ALICE).json()
    assert all_mentors["totalRecords"] == 2

    only_alice = api.get("/v1/mentors?skillId=sk_python&areaId=area_prog", headers=ALICE).json()
    assert [m["id"] for m in only_alice["items"]] == ["alice"]
    assert only_alice["items"][0]["skills"] == ["Python"]

    by_search = api.get("/v1/mentors?search=bob", headers=ALICE).json()
    assert [m["id"] for m in by_search["items"]] == ["bob"]


def test_feed_excludes_own_and_mixes_entities(api, service_payload):
    _seed_two_mentors(api, service_payload)
    feed = api.get("/v1/feed", headers=ALICE).json()
    assert feed["totalRecords"] == 2
    kinds = [item["kind"] for item in feed["items"]]
    assert kinds == ["service", "mentor"]
    assert all(
        item["data"].get("mentorId", item["data"].get("id")) != "alice"
        for item in feed["items"]
    )


def test_recommendations_and_search_history(api, service_payload, core_client):
    _seed_two_mentors(api, service_payload)
    api.post(
        "/v1/services",
        json={
            **service_payload,
            "title": "SQL avanzado",
            "skillIds": ["sk_sql"],
        },
        headers=BOB,
    )

    h_resp = api.post(
        "/v1/me/search-history",
        json={"query": "SQL", "skillId": "sk_sql"},
        headers=ALICE,
    )
    assert h_resp.status_code == 204

    core_client.me_profile = {
        "id": "alice",
        "learningInterests": [{"skillId": "sk_ingles", "name": "Inglés"}],
    }
    recs = api.get("/v1/recommendations", headers=ALICE).json()["items"]
    assert len(recs) == 2  # excluye los servicios propios de alice
    assert recs[0]["service"]["skills"][0]["id"] == "sk_ingles"
    assert "Inglés" in recs[0]["reason"]
    assert "SQL" in recs[1]["reason"]


def test_search_history_validation(api):
    r = api.post("/v1/me/search-history", json={"query": "   "}, headers=ALICE)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"

    by_area = api.post(
        "/v1/me/search-history",
        json={"query": "", "areaId": "area_mec"},
        headers=ALICE,
    )
    assert by_area.status_code == 204


def test_popular_searches_ranks_history_and_fills_from_skills(api, service_payload):
    _seed_two_mentors(api, service_payload)
    r1 = api.post("/v1/me/search-history", json={"query": "SQL"}, headers=ALICE)
    r2 = api.post("/v1/me/search-history", json={"query": "sql"}, headers=BOB)
    r3 = api.post("/v1/me/search-history", json={"query": "Java"}, headers=ALICE)
    assert r1.status_code == 204 and r2.status_code == 204 and r3.status_code == 204

    resp = api.get("/v1/popular-searches?limit=4")
    assert resp.status_code == 200
    items = resp.json()
    assert items[0].lower() == "sql"
    assert items[1] == "Java"
    assert len(items) >= 3
