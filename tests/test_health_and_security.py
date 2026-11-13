from app.core.errors import AppError
from app.core.security import CERT_HEADER, CurrentUser, compute_thumbprint


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "UP"
    assert body["service"] == "ms-dominio-python"
    assert isinstance(body["timestampEpochMs"], int)


def test_unknown_route_uses_standard_error_format(client):
    r = client.get("/no-existe")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "NOT_FOUND"
    assert body["path"] == "/no-existe"
    assert isinstance(body["timestampEpochMs"], int)
    assert body["details"] == []


def test_cert_valid_thumbprint_allows(make_client, apim_cert):
    cert_b64, thumb = apim_cert
    c = make_client(apim_cert_check=True, apim_cert_thumbprint=thumb)
    assert c.get("/health", headers={CERT_HEADER: cert_b64}).status_code == 200


def test_cert_thumbprint_with_colons_and_lowercase_is_accepted(make_client, apim_cert):
    cert_b64, thumb = apim_cert
    formatted = ":".join(thumb[i : i + 2] for i in range(0, len(thumb), 2)).lower()
    c = make_client(apim_cert_check=True, apim_cert_thumbprint=formatted)
    assert c.get("/health", headers={CERT_HEADER: cert_b64}).status_code == 200


def test_cert_missing_is_403(make_client, apim_cert):
    c = make_client(apim_cert_check=True, apim_cert_thumbprint=apim_cert[1])
    r = c.get("/health")
    assert r.status_code == 403
    assert r.json()["code"] == "FORBIDDEN"


def test_cert_wrong_thumbprint_is_403(make_client, apim_cert, other_cert):
    c = make_client(apim_cert_check=True, apim_cert_thumbprint=apim_cert[1])
    r = c.get("/health", headers={CERT_HEADER: other_cert[0]})
    assert r.status_code == 403


def test_cert_garbage_is_403(make_client, apim_cert):
    c = make_client(apim_cert_check=True, apim_cert_thumbprint=apim_cert[1])
    assert c.get("/health", headers={CERT_HEADER: "no-es-base64!!"}).status_code == 403
    assert c.get("/health", headers={CERT_HEADER: "YWJj"}).status_code == 403


def test_cert_check_without_configured_thumbprint_fails_closed(make_client, apim_cert):
    c = make_client(apim_cert_check=True, apim_cert_thumbprint="")
    assert c.get("/health", headers={CERT_HEADER: apim_cert[0]}).status_code == 403


def test_compute_thumbprint_matches(apim_cert):
    assert compute_thumbprint(apim_cert[0]) == apim_cert[1]


def test_current_user_helpers():
    assert CurrentUser(id="u1", role="admin").is_admin
    assert not CurrentUser(id="u1", role="user").is_admin
    assert AppError(404, "NOT_FOUND", "x").status_code == 404
