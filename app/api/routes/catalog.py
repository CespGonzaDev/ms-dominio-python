from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_catalog_service
from app.schemas.catalog import AreaOut, SkillOut
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/v1/catalog", tags=["Catálogo"])

Svc = Annotated[CatalogService, Depends(get_catalog_service)]


@router.get("/areas", response_model=list[AreaOut])
def list_areas(svc: Svc):
    return svc.list_areas()


@router.get("/skills", response_model=list[SkillOut])
def list_skills(
    svc: Svc,
    area_id: Annotated[str | None, Query(alias="areaId")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
):
    return svc.list_skills(area_id=area_id, search=search)
