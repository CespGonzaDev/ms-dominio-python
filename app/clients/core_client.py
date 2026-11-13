"""Cliente HTTP hacia ms-core (usuarios, sesiones y suspensión administrativa)."""

import logging
from typing import Protocol

import httpx

from app.core.errors import AppError

logger = logging.getLogger(__name__)


class CoreGateway(Protocol):
    """Puerto hacia ms-core. Permite inyectar dobles en pruebas sin red."""

    def get_session(self, session_id: str, headers: dict[str, str]) -> dict: ...

    def get_user(self, user_id: str, headers: dict[str, str]) -> dict | None: ...

    def get_me(self, headers: dict[str, str]) -> dict | None: ...

    def suspend_user(self, user_id: str, reason: str, headers: dict[str, str]) -> bool: ...


def _normalize_base(url: str) -> str:
    base = url.strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return base


class HttpCoreClient:
    """Cliente real contra ms-core usando httpx y suscripción de APIM."""

    def __init__(self, base_url: str, subscription_key: str = "", timeout: float = 5.0) -> None:
        self._base = _normalize_base(base_url) if base_url else ""
        self._sub_key = subscription_key
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._base)

    def _headers(self, caller_headers: dict[str, str]) -> dict[str, str]:
        out = dict(caller_headers)
        if self._sub_key:
            out["Ocp-Apim-Subscription-Key"] = self._sub_key
        return out

    def _request(
        self, method: str, path: str, caller_headers: dict[str, str], **kwargs
    ) -> httpx.Response:
        with httpx.Client(timeout=self._timeout) as client:
            return client.request(
                method,
                f"{self._base}{path}",
                headers=self._headers(caller_headers),
                **kwargs,
            )

    def get_session(self, session_id: str, headers: dict[str, str]) -> dict:
        if not self.enabled:
            raise AppError(503, "CORE_UNAVAILABLE", "Integración con ms-core no configurada")
        try:
            resp = self._request("GET", f"/v1/sessions/{session_id}", headers)
        except httpx.HTTPError as exc:
            logger.warning("Error consultando sesión %s en ms-core: %s", session_id, exc)
            raise AppError(
                502, "UPSTREAM_ERROR", "No se pudo consultar la sesión en ms-core"
            ) from exc

        if resp.status_code == 404:
            raise AppError(404, "SESSION_NOT_FOUND", f"La sesión '{session_id}' no existe")
        if resp.status_code == 403:
            raise AppError(403, "FORBIDDEN", "No tienes acceso a esta sesión")
        if resp.status_code == 401:
            raise AppError(401, "UNAUTHORIZED", "Identidad no autorizada por ms-core")
        if resp.status_code >= 400:
            raise AppError(502, "UPSTREAM_ERROR", "ms-core devolvió un error al validar la sesión")
        return resp.json()

    def _safe_get_json(self, path: str, headers: dict[str, str]) -> dict | None:
        if not self.enabled:
            return None
        try:
            resp = self._request("GET", path, headers)
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Fallo opcional consultando %s en ms-core: %s", path, exc)
        return None

    def get_user(self, user_id: str, headers: dict[str, str]) -> dict | None:
        return self._safe_get_json(f"/v1/users/{user_id}", headers)

    def get_me(self, headers: dict[str, str]) -> dict | None:
        return self._safe_get_json("/v1/me", headers)

    def suspend_user(self, user_id: str, reason: str, headers: dict[str, str]) -> bool:
        if not self.enabled:
            return False
        try:
            resp = self._request(
                "PATCH",
                f"/v1/admin/users/{user_id}/status",
                headers,
                json={"status": "suspended", "reason": reason},
            )
            return resp.status_code < 400
        except httpx.HTTPError as exc:
            logger.warning("No se pudo suspender usuario %s en ms-core: %s", user_id, exc)
            return False
