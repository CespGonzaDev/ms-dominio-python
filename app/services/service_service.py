"""Lógica de negocio de servicios de mentoría."""

import uuid

from app.clients.core_client import CoreGateway
from app.core.errors import AppError, now_epoch_ms
from app.core.security import CurrentUser
from app.repositories.protocols import CatalogRepository, ServiceRepository
from app.schemas.service import (
    ServiceCreate,
    ServiceFilters,
    ServiceStatus,
    ServiceUpdate,
)

_DAY_LABELS = ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")


def format_availability_summary(days: list[int], override: str | None = None) -> str:
    if override:
        return override
    if not days:
        return "Por coordinar"
    return ", ".join(_DAY_LABELS[d] for d in sorted(set(days)) if 0 <= d <= 6)


class ServiceService:
    def __init__(
        self,
        repo: ServiceRepository,
        catalog_repo: CatalogRepository,
        core_client: CoreGateway | None = None,
    ) -> None:
        self._repo = repo
        self._catalog = catalog_repo
        self._core = core_client

    def search(self, filters: ServiceFilters) -> tuple[int, list[dict]]:
        return self._repo.search(filters, active_only=True)

    def get(self, service_id: str) -> dict:
        doc = self._repo.get(service_id)
        if doc is None or doc.get("deleted"):
            raise AppError(404, "NOT_FOUND", f"El servicio '{service_id}' no existe")
        return doc

    def list_mine(self, user: CurrentUser, filters: ServiceFilters) -> tuple[int, list[dict]]:
        scoped = ServiceFilters(
            mentor_id=user.id,
            status=filters.status,
            area_id=filters.area_id,
            search=filters.search,
            sort=filters.sort,
            page=filters.page,
            page_size=filters.page_size,
        )
        return self._repo.list_by_mentor(user.id, scoped)

    def create(self, user: CurrentUser, data: ServiceCreate) -> dict:
        area, skills = self._resolve_catalog(data.area_id, data.skill_ids)
        mentor, headline, institution = self._resolve_mentor_info(user)
        now = now_epoch_ms()
        payload = self._serialize_fields(data, area, skills)
        doc = {
            "id": str(uuid.uuid4()),
            "mentorId": user.id,
            "mentor": mentor,
            "mentorHeadline": headline,
            "mentorInstitution": institution,
            "status": "activo",
            "deleted": False,
            "createdAtEpochMs": now,
            "updatedAtEpochMs": now,
            **payload,
        }
        return self._repo.create(doc)

    def update(self, user: CurrentUser, service_id: str, data: ServiceUpdate) -> dict:
        doc = self._owned(user, service_id)
        area, skills = self._resolve_catalog(data.area_id, data.skill_ids)
        doc.update(self._serialize_fields(data, area, skills))
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

    def _resolve_catalog(self, area_id: str, skill_ids: list[str]) -> tuple[dict, list[dict]]:
        areas = {a["id"]: a for a in self._catalog.list_by_type("area")}
        if area_id not in areas:
            raise AppError(400, "INVALID_AREA", f"El área '{area_id}' no existe")

        skills_by_id = {s["id"]: s for s in self._catalog.list_by_type("skill")}
        resolved_skills: list[dict] = []
        for sid in dict.fromkeys(skill_ids):
            skill = skills_by_id.get(sid)
            if skill is None:
                raise AppError(400, "INVALID_SKILL", f"La habilidad '{sid}' no existe")
            resolved_skills.append(
                {"id": skill["id"], "name": skill["name"], "areaId": skill.get("areaId")}
            )

        area = areas[area_id]
        clean_area = {"id": area["id"], "name": area["name"]}
        if area.get("icon"):
            clean_area["icon"] = area["icon"]
        return clean_area, resolved_skills

    def _resolve_mentor_info(self, user: CurrentUser) -> tuple[dict, str, str]:
        _, existing = self._repo.list_by_mentor(user.id)
        prev_mentor = existing[0].get("mentor", {}) if existing else {}
        headline = existing[0].get("mentorHeadline", "") if existing else ""
        institution = existing[0].get("mentorInstitution", "") if existing else ""

        rating_avg = float(prev_mentor.get("ratingAverage", 0.0))
        rating_cnt = int(prev_mentor.get("ratingCount", 0))
        full_name = user.name or prev_mentor.get("fullName") or user.id
        avatar_url = user.avatar if user.avatar is not None else prev_mentor.get("avatarUrl")

        if self._core:
            core_user = self._core.get_user(user.id, user.forward_headers())
            if core_user:
                full_name = core_user.get("fullName") or full_name
                avatar_url = core_user.get("avatarUrl", avatar_url)
                academic = core_user.get("academic") or {}
                prof = core_user.get("professional") or {}
                headline = prof.get("occupation") or academic.get("career") or headline
                institution = academic.get("institution") or institution

        mentor = {
            "id": user.id,
            "fullName": full_name,
            "avatarUrl": avatar_url,
            "ratingAverage": rating_avg,
            "ratingCount": rating_cnt,
        }
        return mentor, headline, institution

    @staticmethod
    def _serialize_fields(
        data: ServiceCreate | ServiceUpdate, area: dict, skills: list[dict]
    ) -> dict:
        dumped = data.model_dump(by_alias=True)
        skill_ids = [s["id"] for s in skills]
        return {
            "title": dumped["title"],
            "description": dumped["description"],
            "areaId": area["id"],
            "area": area,
            "skillIds": skill_ids,
            "skills": skills,
            "durationMinutes": dumped["durationMinutes"],
            "type": dumped["type"],
            "capacity": dumped["capacity"],
            "modality": dumped["modality"],
            "platforms": dumped["platforms"],
            "price": dumped["price"],
            "availableDays": dumped["availableDays"],
            "availabilitySummary": format_availability_summary(
                dumped["availableDays"], dumped.get("availabilitySummary")
            ),
        }
