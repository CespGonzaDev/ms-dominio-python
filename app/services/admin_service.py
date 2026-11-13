"""Lógica de administración: moderación de servicios, reportes y estadísticas."""

from collections import Counter

from app.clients.core_client import CoreGateway
from app.core.errors import AppError, now_epoch_ms
from app.core.security import CurrentUser
from app.repositories.protocols import ReportRepository, ReviewRepository, ServiceRepository
from app.schemas.admin import AdminReportPatch, AdminServiceStatusPatch
from app.services.rating_helper import recalculate_mentor_rating


def _paginate(items: list, page: int, page_size: int) -> tuple[int, list]:
    offset = (page - 1) * page_size
    return len(items), items[offset : offset + page_size]


class AdminService:
    def __init__(
        self,
        service_repo: ServiceRepository,
        report_repo: ReportRepository,
        review_repo: ReviewRepository,
        core_client: CoreGateway | None = None,
    ) -> None:
        self._services = service_repo
        self._reports = report_repo
        self._reviews = review_repo
        self._core = core_client

    def list_services(
        self,
        *,
        search: str | None = None,
        status: str | None = None,
        reported: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[dict]]:
        services = self._services.list_all()
        service_reports = self._reports.list_filtered(target_type="service")
        report_counts = Counter(r["targetId"] for r in service_reports)

        needle = search.strip().lower() if search else None
        rows: list[dict] = []
        for svc in services:
            if status and svc.get("status") != status:
                continue
            count = report_counts.get(svc["id"], 0)
            if reported is True and count == 0:
                continue
            if reported is False and count > 0:
                continue
            if needle:
                mentor_name = (svc.get("mentor") or {}).get("fullName", "")
                if needle not in f"{svc.get('title', '')} {mentor_name}".lower():
                    continue
            rows.append({**svc, "reportsCount": count})

        rows.sort(key=lambda r: (-r["reportsCount"], -r.get("updatedAtEpochMs", 0)))
        return _paginate(rows, page, page_size)

    def set_service_status(self, service_id: str, data: AdminServiceStatusPatch) -> dict:
        doc = self._services.get(service_id)
        if doc is None or doc.get("deleted"):
            raise AppError(404, "NOT_FOUND", f"El servicio '{service_id}' no existe")
        doc["status"] = data.status
        doc["moderationReason"] = data.reason
        doc["updatedAtEpochMs"] = now_epoch_ms()
        updated = self._services.replace(doc)
        reports = [
            r
            for r in self._reports.list_filtered(target_type="service")
            if r["targetId"] == service_id
        ]
        return {**updated, "reportsCount": len(reports)}

    def list_reports(
        self,
        *,
        status: str | None = None,
        target_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[dict]]:
        items = self._reports.list_filtered(status=status, target_type=target_type, search=search)
        return _paginate(items, page, page_size)

    def update_report(self, user: CurrentUser, report_id: str, data: AdminReportPatch) -> dict:
        doc = self._reports.get(report_id)
        if doc is None:
            raise AppError(404, "NOT_FOUND", f"El reporte '{report_id}' no existe")

        old_status = doc["status"]
        updated = dict(doc)
        updated["status"] = data.status
        if data.resolution is not None:
            updated["resolution"] = data.resolution
        if data.action_taken is not None:
            updated["actionTaken"] = data.action_taken

        if data.status in ("resuelto", "descartado"):
            updated["resolvedAtEpochMs"] = updated.get("resolvedAtEpochMs") or now_epoch_ms()
        else:
            updated.pop("resolvedAtEpochMs", None)

        self._apply_action(
            user,
            updated["targetType"],
            updated["targetId"],
            data.action_taken,
            data.resolution or "Acción administrativa",
        )
        return self._reports.save_with_status(old_status, updated)

    def stats(self) -> dict:
        all_services = self._services.list_all()
        active_services = [s for s in all_services if s.get("status") == "activo"]
        ratings = self._reviews.list_visible_ratings()
        avg = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

        area_counts: Counter[str] = Counter()
        areas_by_id: dict[str, dict] = {}
        for svc in active_services:
            area = svc.get("area")
            if area and area.get("id"):
                aid = area["id"]
                areas_by_id[aid] = area
                area_counts[aid] += 1

        top_areas = [
            {"area": areas_by_id[aid], "services": count}
            for aid, count in area_counts.most_common(5)
        ]
        return {
            "services": {"total": len(all_services), "active": len(active_services)},
            "reviews": {"total": len(ratings), "average": avg},
            "topAreas": top_areas,
        }

    def _apply_action(
        self,
        user: CurrentUser,
        target_type: str,
        target_id: str,
        action_taken: str | None,
        reason: str,
    ) -> None:
        if not action_taken or action_taken == "ninguna":
            return
        if action_taken == "desactivar_servicio" and target_type == "service":
            svc = self._services.get(target_id)
            if svc and not svc.get("deleted"):
                svc["status"] = "inactivo"
                svc["moderationReason"] = reason
                svc["updatedAtEpochMs"] = now_epoch_ms()
                self._services.replace(svc)
        elif action_taken == "ocultar_resena" and target_type == "review":
            rev = self._reviews.get(target_id)
            if rev:
                rev["hidden"] = True
                self._reviews.replace(rev)
                recalculate_mentor_rating(rev["mentorId"], self._reviews, self._services)
        elif action_taken == "suspender_usuario" and target_type == "user":
            _, user_services = self._services.list_by_mentor(target_id)
            now = now_epoch_ms()
            for svc in user_services:
                if svc.get("status") != "inactivo":
                    svc["status"] = "inactivo"
                    svc["moderationReason"] = reason
                    svc["updatedAtEpochMs"] = now
                    self._services.replace(svc)
            if self._core:
                self._core.suspend_user(target_id, reason, user.forward_headers())
