from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_report_service
from app.core.security import CurrentUser, get_current_user
from app.schemas.report import ReportCreate, ReportOut
from app.services.report_service import ReportService

router = APIRouter(prefix="/v1", tags=["Reportes"])

Svc = Annotated[ReportService, Depends(get_report_service)]
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/reports", response_model=ReportOut, status_code=201)
def create_report(body: ReportCreate, user: User, svc: Svc):
    return svc.create(user, body)
