import uuid

from app.core.errors import AppError, now_epoch_ms
from app.core.security import CurrentUser
from app.repositories.protocols import ServiceRepository
from app.schemas.service import (
    ServiceCreate,
    ServiceFilters,
    ServiceStatus,
    ServiceUpdate,
)


class ServiceService:
    def __init__(self, repo: ServiceRepository) -> None:
        self._repo = repo

    # ---- consultas -------------------------------------------------------------------------
    def search(self, filters: ServiceFilters) -> tuple[int, list[dict]]:
        return self._repo.search(filters)

    def get(self, service_id: str) -> dict:
        doc = self._repo.get(service_id)
        if doc is None:
            raise AppError(404, "NOT_FOUND", f"El servicio '{service_id}' no existe")
        return doc

    def list_mine(self, user: CurrentUser) -> list[dict]:
        return self._repo.list_by_mentor(user.id)

    # ---- escritura (solo el dueño) ---------------------------------------------------------
    def create(self, user: CurrentUser, data: ServiceCreate) -> dict:
        now = now_epoch_ms()
        doc = {
            "id": str(uuid.uuid4()),
            "mentorId": user.id,
            "mentor": {"id": user.id, "name": user.name, "avatar": user.avatar},
            "status": "active",
            "rating": 0,
            "reviewCount": 0,
            "createdAtEpochMs": now,
            "updatedAtEpochMs": now,
            **data.model_dump(by_alias=True),
        }
        return self._repo.create(doc)

    def update(self, user: CurrentUser, service_id: str, data: ServiceUpdate) -> dict:
        doc = self._owned(user, service_id)
        doc.update(data.model_dump(by_alias=True))
        doc["updatedAtEpochMs"] = now_epoch_ms()
        return self._repo.replace(doc)

    def set_status(self, user: CurrentUser, service_id: str, status: ServiceStatus) -> dict:
        doc = self._owned(user, service_id)
        doc["status"] = status
        doc["updatedAtEpochMs"] = now_epoch_ms()
        return self._repo.replace(doc)

    def delete(self, user: CurrentUser, service_id: str) -> None:
        doc = self._owned(user, service_id)
        self._repo.delete(service_id, doc["mentorId"])

    def _owned(self, user: CurrentUser, service_id: str) -> dict:
        doc = self.get(service_id)
        if doc["mentorId"] != user.id:
            raise AppError(403, "FORBIDDEN", "Solo el dueño puede modificar este servicio")
        return doc
