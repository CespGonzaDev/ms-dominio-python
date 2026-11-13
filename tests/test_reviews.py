from tests.conftest import ALICE, BOB


def test_create_review_validates_session_and_updates_rating(api, service_payload, core_client):
    svc = api.post("/v1/services", json=service_payload, headers=ALICE).json()
    core_client.sessions["ses_1"] = {
        "id": "ses_1",
        "status": "completada",
        "mentor": {"id": "alice", "fullName": "Alice"},
        "learners": [{"id": "bob", "fullName": "Bob"}],
    }
    created = api.post(
        "/v1/sessions/ses_1/review",
        json={"rating": 5, "comment": "Excelente explicación de principio a fin."},
        headers=BOB,
    )
    assert created.status_code == 201, created.text
    rev = created.json()
    assert rev["mentorId"] == "alice"
    assert rev["learner"]["id"] == "bob"
    assert isinstance(rev["createdAtEpochMs"], int)

    # Propaga calificación al servicio del mentor
    refreshed = api.get(f"/v1/services/{svc['id']}", headers=BOB).json()
    assert refreshed["mentor"]["ratingAverage"] == 5.0
    assert refreshed["mentor"]["ratingCount"] == 1

    # Duplicado rechazado
    dup = api.post(
        "/v1/sessions/ses_1/review",
        json={"rating": 4, "comment": "Intentando duplicar la reseña anterior."},
        headers=BOB,
    )
    assert dup.status_code == 400 and dup.json()["code"] == "ALREADY_REVIEWED"


def test_create_review_error_cases(api, core_client):
    assert (
        api.post(
            "/v1/sessions/missing/review",
            json={"rating": 5, "comment": "Muy buena sesión de prueba."},
            headers=BOB,
        ).status_code
        == 404
    )

    core_client.sessions["ses_pending"] = {
        "id": "ses_pending",
        "status": "pendiente",
        "mentor": {"id": "alice"},
        "learners": [{"id": "bob", "fullName": "Bob"}],
    }
    not_done = api.post(
        "/v1/sessions/ses_pending/review",
        json={"rating": 5, "comment": "Muy buena sesión de prueba."},
        headers=BOB,
    )
    assert not_done.status_code == 400 and not_done.json()["code"] == "SESSION_NOT_COMPLETED"

    core_client.sessions["ses_other"] = {
        "id": "ses_other",
        "status": "completada",
        "mentor": {"id": "alice"},
        "learners": [{"id": "carol", "fullName": "Carol"}],
    }
    forbidden = api.post(
        "/v1/sessions/ses_other/review",
        json={"rating": 5, "comment": "No participé en esta sesión."},
        headers=BOB,
    )
    assert forbidden.status_code == 403


def _learner(uid: str, name: str) -> dict:
    return {
        "id": uid,
        "fullName": name,
        "avatarUrl": None,
        "ratingAverage": 0,
        "ratingCount": 0,
    }


def test_user_reviews_and_rating_summary(api, review_repo):
    review_repo.docs = {
        "r1": {
            "id": "r1",
            "sessionId": "s1",
            "mentorId": "alice",
            "learnerId": "bob",
            "learner": _learner("bob", "Bob"),
            "rating": 5,
            "comment": "Muy clara la tutoría y los ejemplos.",
            "hidden": False,
            "createdAtEpochMs": 2_000,
        },
        "r2": {
            "id": "r2",
            "sessionId": "s2",
            "mentorId": "alice",
            "learnerId": "carol",
            "learner": _learner("carol", "Carol"),
            "rating": 4,
            "comment": "Buena sesión con ejercicios prácticos.",
            "hidden": False,
            "createdAtEpochMs": 1_000,
        },
        "r_hidden": {
            "id": "r_hidden",
            "sessionId": "s3",
            "mentorId": "alice",
            "learnerId": "dave",
            "learner": _learner("dave", "Dave"),
            "rating": 1,
            "comment": "Reseña ocultada por moderación.",
            "hidden": True,
            "createdAtEpochMs": 3_000,
        },
    }

    page = api.get("/v1/users/alice/reviews", headers=BOB).json()
    assert page["totalRecords"] == 2
    assert [r["id"] for r in page["items"]] == ["r1", "r2"]

    only5 = api.get("/v1/users/alice/reviews?rating=5", headers=BOB).json()
    assert [r["id"] for r in only5["items"]] == ["r1"]

    summary = api.get("/v1/users/alice/rating-summary", headers=BOB).json()
    assert summary == {
        "average": 4.5,
        "count": 2,
        "distribution": {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1},
    }
