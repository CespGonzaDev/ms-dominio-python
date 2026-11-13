"""Seguridad: validación del certificado de APIM (mTLS) e identidad del usuario.

App Service NO valida el certificado por sí solo: lo reenvía en el header
`X-ARR-ClientCert` (DER en base64). Aquí se compara su huella SHA-1 con
`APIM_CERT_THUMBPRINT`.
"""

import base64
import binascii
from dataclasses import dataclass
from typing import Annotated

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from fastapi import Depends, Header

from app.core.config import Settings, get_settings
from app.core.errors import AppError

CERT_HEADER = "X-ARR-ClientCert"


def _forbidden(message: str) -> AppError:
    return AppError(403, "FORBIDDEN", message)


def compute_thumbprint(cert_b64: str) -> str:
    """Huella SHA-1 (hex en mayúsculas, sin ':') de un certificado DER en base64."""
    try:
        der = base64.b64decode(cert_b64, validate=True)
        cert = x509.load_der_x509_certificate(der)
    except (binascii.Error, ValueError) as exc:
        raise _forbidden("Certificado de cliente inválido") from exc
    return cert.fingerprint(hashes.SHA1()).hex().upper()  # noqa: S303


def verify_apim_cert(
    settings: Annotated[Settings, Depends(get_settings)],
    x_arr_clientcert: Annotated[str | None, Header(alias=CERT_HEADER)] = None,
) -> None:
    """Dependencia global: solo se acepta tráfico que presente el certificado de APIM."""
    if not settings.apim_cert_check:
        return
    expected = settings.apim_cert_thumbprint.replace(":", "").strip().upper()
    if not expected:
        # Configuración incompleta: fallar cerrado, nunca abierto.
        raise _forbidden("Validación de certificado sin huella configurada")
    if not x_arr_clientcert:
        raise _forbidden("Se requiere el certificado de APIM")
    if compute_thumbprint(x_arr_clientcert) != expected:
        raise _forbidden("Certificado de cliente no autorizado")


@dataclass(frozen=True)
class CurrentUser:
    id: str
    role: str
    name: str | None = None
    avatar: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def get_current_user(
    x_user_id: Annotated[str | None, Header()] = None,
    x_user_role: Annotated[str | None, Header()] = None,
    x_user_name: Annotated[str | None, Header()] = None,
    x_user_avatar: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Identidad inyectada por APIM (X-User-Id del JWT). El backend no decodifica el token.

    X-User-Role / X-User-Name / X-User-Avatar son opcionales y requieren que APIM los inyecte
    desde los claims role, name y avatar del JWT (pendiente de acordar con P4).
    """
    if not x_user_id:
        raise AppError(401, "UNAUTHORIZED", "Falta la identidad del usuario")
    role = (x_user_role or "user").strip().lower()
    return CurrentUser(id=x_user_id, role=role, name=x_user_name, avatar=x_user_avatar)


def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if not user.is_admin:
        raise _forbidden("Se requiere rol de administrador")
    return user
