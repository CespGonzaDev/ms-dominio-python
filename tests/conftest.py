import base64

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient

from app.api.deps import get_catalog_repo, get_service_repo
from app.core.config import Settings, get_settings
from app.main import create_app
from tests.fakes import FakeCatalogRepository, FakeServiceRepository


def _make_cert(cn: str) -> tuple[str, str]:
    """Genera un certificado autofirmado; devuelve (DER en base64, huella SHA-1 en hex)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    import datetime as dt

    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + dt.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    der = cert.public_bytes(serialization.Encoding.DER)
    return base64.b64encode(der).decode(), cert.fingerprint(hashes.SHA1()).hex().upper()


@pytest.fixture(scope="session")
def apim_cert() -> tuple[str, str]:
    return _make_cert("apim-test")


@pytest.fixture(scope="session")
def other_cert() -> tuple[str, str]:
    return _make_cert("atacante")


@pytest.fixture
def make_client():
    """Crea un cliente con settings a medida (sobrescribe la dependencia get_settings)."""

    def _factory(**overrides) -> TestClient:
        app = create_app()
        settings = Settings(_env_file=None, **overrides)
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app, raise_server_exceptions=False)

    return _factory


@pytest.fixture
def client(make_client) -> TestClient:
    """Cliente en modo local: sin validación de certificado."""
    return make_client(apim_cert_check=False)


ALICE = {"X-User-Id": "alice", "X-User-Name": "Alice", "X-User-Avatar": "a.png"}
BOB = {"X-User-Id": "bob"}


@pytest.fixture
def catalog_repo() -> FakeCatalogRepository:
    return FakeCatalogRepository()


@pytest.fixture
def service_repo() -> FakeServiceRepository:
    return FakeServiceRepository()


@pytest.fixture
def api(make_client, catalog_repo, service_repo) -> TestClient:
    """Cliente con repositorios falsos inyectados (sin Cosmos)."""
    c = make_client(apim_cert_check=False)
    c.app.dependency_overrides[get_catalog_repo] = lambda: catalog_repo
    c.app.dependency_overrides[get_service_repo] = lambda: service_repo
    return c


@pytest.fixture
def service_payload() -> dict:
    return {
        "title": "Mentoría de Python",
        "description": "Aprende lo básico",
        "areaId": "tech",
        "skillIds": ["python"],
        "type": "individual",
        "modality": "online",
        "platforms": ["zoom"],
        "durationMinutes": 60,
        "capacity": 1,
        "price": 10,
        "availableDays": ["monday"],
    }
