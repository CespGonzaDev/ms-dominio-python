"""Lógica de negocio de reportes."""

import uuid

from app.clients.core_client import CoreGateway
from app.core.errors import AppError, now_epoch_ms
from app.core.security import CurrentUser
from app.repositories.protocols import ReportRepository, ReviewRepository, ServiceRepository
from app.schemas.report import ReportCreate


class ReportService:
    def __init__(
        self,
        report_repo: ReportRepository,
        service_repo: ServiceRepository,
        review_repo: ReviewRepository,
        core_client: CoreGateway | None = None,
    ) -> None:
        self._reports = report_repo
        self._services = service_repo
        self._reviews = review_repo
        self._core = core_client

    def create(self, user: CurrentUser, data: ReportCreate) -> dict:
        target_label = self._resolve_target_label(user, data.target_type, data.target_id)
        reporter = self._resolve_reporter(user)
        doc = {
            "id": str(uuid.uuid4()),
            "reporterId": user.id,
            "reporter": reporter,
            "targetType": data.target_type,
            "targetId": data.target_id,
            "targetLabel": target_label,
            "reason": data.reason,
            "description": data.description,
            "status": "pendiente",
            "createdAtEpochMs": now_epoch_ms(),
        }
        return self._reports.create(doc)

    def _resolve_target_label(self, user: CurrentUser, target_type: str, target_id: str) -> str:
        if target_type == "service":
            svc = self._services.get(target_id)
            if svc is None or svc.get("deleted"):
                raise AppError(404, "NOT_FOUND", f"El servicio '{target_id}' no existe")
            return svc["title"]

        if target_type == "review":
            rev = self._reviews.get(target_id)
            if rev is None:
                raise AppError(404, "NOT_FOUND", f"La reseña '{target_id}' no existe")
            _, mentor_svcs = self._services.list_by_mentor(rev["mentorId"])
            mentor_name = (
                (mentor_svcs[0].get("mentor") or {}).get("fullName")
                if mentor_svcs
                else rev["mentorId"]
            )
            return f"Reseña a {mentor_name}"

        # target_type == "user"
        if self._core:
            core_user = self._core.get_user(target_id, user.forward_headers())
            if core_user and core_user.get("fullName"):
                return core_user["fullName"]
        _, mentor_svcs = self._services.list_by_mentor(target_id)
        if mentor_svcs:
            return (mentor_svcs[0].get("mentor") or {}).get("fullName") or target_id
        return f"Usuario {target_id}"

    def _resolve_reporter(self, user: CurrentUser) -> dict:
        full_name = user.name
        avatar_url = user.avatar
        if not full_name and self._core:
            core_user = self._core.get_user(user.id, user.forward_headers())
            if core_user:
                full_name = core_user.get("fullName")
                avatar_url = core_user.get("avatarUrl", avatar_url)
        return {
            "id": user.id,
            "fullName": full_name or user.id,
            "avatarUrl": avatar_url,
            "ratingAverage": 0.0,
            "ratingCount": 0,
        }
