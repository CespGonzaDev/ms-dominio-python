from tests.conftest import ADMIN, ALICE, BOB


def test_create_report_and_missing_target(api, service_payload):
    svc = api.post("/v1/services", json=service_payload, headers=ALICE).json()

    created = api.post(
        "/v1/reports",
        json={
            "targetType": "service",
            "targetId": svc["id"],
            "reason": "spam",
            "description": "Tiene enlaces externos que no corresponden al curso.",
        },
        headers=BOB,
    )
    assert created.status_code == 201, created.text
    rep = created.json()
    assert rep["status"] == "pendiente"
    assert rep["targetLabel"] == svc["title"]
    assert rep["reporter"]["id"] == "bob"

    missing = api.post(
        "/v1/reports",
        json={
            "targetType": "service",
            "targetId": "nope",
            "reason": "spam",
            "description": "Reporte sobre un servicio que ya no existe.",
        },
        headers=BOB,
    )
    assert missing.status_code == 404


def test_admin_endpoints_reject_non_admin(api):
    for method, path in (
        ("GET", "/v1/admin/services"),
        ("PATCH", "/v1/admin/services/s1/status"),
        ("GET", "/v1/admin/reports"),
        ("PATCH", "/v1/admin/reports/r1"),
        ("GET", "/v1/admin/stats"),
    ):
        body = {"status": "inactivo", "reason": "motivo de prueba"} if method == "PATCH" else None
        resp = api.request(method, path, headers=BOB, json=body)
        assert resp.status_code == 403, (method, path)


def test_admin_service_moderation_and_report_actions(
    api, service_payload, review_repo, core_client
):
    svc = api.post("/v1/services", json=service_payload, headers=ALICE).json()
    review_repo.docs["rev_1"] = {
        "id": "rev_1",
        "sessionId": "ses_1",
        "mentorId": "alice",
        "learnerId": "bob",
        "learner": {
            "id": "bob",
            "fullName": "Bob",
            "avatarUrl": None,
            "ratingAverage": 0,
            "ratingCount": 0,
        },
        "rating": 2,
        "comment": "Comentario problemático reportado.",
        "hidden": False,
        "createdAtEpochMs": 1_000,
    }

    rep_svc = api.post(
        "/v1/reports",
        json={
            "targetType": "service",
            "targetId": svc["id"],
            "reason": "fraude",
            "description": "Descripción fraudulenta detectada en el catálogo.",
        },
        headers=BOB,
    ).json()

    rep_rev = api.post(
        "/v1/reports",
        json={
            "targetType": "review",
            "targetId": "rev_1",
            "reason": "acoso",
            "description": "Lenguaje ofensivo dentro de la reseña.",
        },
        headers=ALICE,
    ).json()

    admin_svcs = api.get("/v1/admin/services?reported=true", headers=ADMIN).json()
    assert admin_svcs["totalRecords"] == 1
    assert admin_svcs["items"][0]["reportsCount"] == 1

    # Resolver reporte de servicio desactivándolo (prueba también migración de partición /status)
    resolved_svc = api.patch(
        f"/v1/admin/reports/{rep_svc['id']}",
        json={
            "status": "resuelto",
            "resolution": "Se desactiva el servicio por incumplir términos.",
            "actionTaken": "desactivar_servicio",
        },
        headers=ADMIN,
    )
    assert resolved_svc.status_code == 200
    assert resolved_svc.json()["status"] == "resuelto"
    assert isinstance(resolved_svc.json()["resolvedAtEpochMs"], int)
    assert api.get(f"/v1/services/{svc['id']}", headers=BOB).json()["status"] == "inactivo"

    # Reactivar manualmente desde moderación de servicios
    reactivated = api.patch(
        f"/v1/admin/services/{svc['id']}/status",
        json={"status": "activo", "reason": "El mentor corrigió la descripción"},
        headers=ADMIN,
    )
    assert reactivated.status_code == 200 and reactivated.json()["status"] == "activo"

    # Ocultar reseña vía reporte y recalcular rating del mentor
    resolved_rev = api.patch(
        f"/v1/admin/reports/{rep_rev['id']}",
        json={
            "status": "resuelto",
            "resolution": "Reseña ocultada",
            "actionTaken": "ocultar_resena",
        },
        headers=ADMIN,
    )
    assert resolved_rev.status_code == 200
    assert review_repo.docs["rev_1"]["hidden"] is True

    # Suspender usuario reportado
    rep_user = api.post(
        "/v1/reports",
        json={
            "targetType": "user",
            "targetId": "alice",
            "reason": "acoso",
            "description": "Incumplimiento reiterado en sesiones.",
        },
        headers=BOB,
    ).json()
    api.patch(
        f"/v1/admin/reports/{rep_user['id']}",
        json={
            "status": "resuelto",
            "resolution": "Cuenta suspendida",
            "actionTaken": "suspender_usuario",
        },
        headers=ADMIN,
    )
    assert core_client.suspended == [("alice", "Cuenta suspendida")]
    assert api.get(f"/v1/services/{svc['id']}", headers=BOB).json()["status"] == "inactivo"

    stats = api.get("/v1/admin/stats", headers=ADMIN).json()
    assert stats["services"] == {"total": 1, "active": 0}
    assert stats["reviews"] == {"total": 0, "average": 0.0}
