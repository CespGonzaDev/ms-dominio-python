from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_admin_service
from app.core.security import CurrentUser, require_admin
from app.schemas.admin import (
    AdminReportPatch,
    AdminServiceRowOut,
    AdminServiceStatusPatch,
    AdminStatsOut,
)
from app.schemas.common import Page
from app.schemas.report import ReportOut, ReportStatus, ReportTargetType
from app.schemas.service import ServiceStatus
from app.services.admin_service import AdminService

router = APIRouter(prefix="/v1/admin", tags=["Administración"])

Svc = Annotated[AdminService, Depends(get_admin_service)]
Admin = Annotated[CurrentUser, Depends(require_admin)]


@router.get("/services", response_model=Page[AdminServiceRowOut])
def admin_list_services(
    _: Admin,
    svc: Svc,
    search: Annotated[str | None, Query(max_length=100)] = None,
    status: ServiceStatus | None = None,
    reported: bool | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
):
    total, items = svc.list_services(
        search=search, status=status, reported=reported, page=page, page_size=page_size
    )
    return Page[AdminServiceRowOut](
        total_records=total, page=page, page_size=page_size, items=items
    )


@router.patch("/services/{service_id}/status", response_model=AdminServiceRowOut)
def admin_patch_service_status(
    service_id: str, body: AdminServiceStatusPatch, _: Admin, svc: Svc
):
    return svc.set_service_status(service_id, body)


@router.get("/reports", response_model=Page[ReportOut])
def admin_list_reports(
    _: Admin,
    svc: Svc,
    status: ReportStatus | None = None,
    target_type: Annotated[ReportTargetType | None, Query(alias="targetType")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
):
    total, items = svc.list_reports(
        status=status, target_type=target_type, search=search, page=page, page_size=page_size
    )
    return Page[ReportOut](total_records=total, page=page, page_size=page_size, items=items)


@router.patch("/reports/{report_id}", response_model=ReportOut)
def admin_update_report(report_id: str, body: AdminReportPatch, admin: Admin, svc: Svc):
    return svc.update_report(admin, report_id, body)


@router.get("/stats", response_model=AdminStatsOut)
def admin_stats(_: Admin, svc: Svc):
    return svc.stats()
