from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_catalog_service
from app.core.security import CurrentUser, get_current_user
from app.schemas.catalog import AreaOut, SkillOut
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/v1/catalog", tags=["Catálogo"])

Svc = Annotated[CatalogService, Depends(get_catalog_service)]
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/areas", response_model=list[AreaOut])
def list_areas(_: User, svc: Svc):
    return svc.list_areas()


@router.get("/skills", response_model=list[SkillOut])
def list_skills(
    _: User,
    svc: Svc,
    area_id: Annotated[str | None, Query(alias="areaId")] = None,
):
    return svc.list_skills(area_id)
