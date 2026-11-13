from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_service_service
from app.core.security import CurrentUser, get_current_user
from app.schemas.common import Page
from app.schemas.service import (
    Modality,
    ServiceCreate,
    ServiceFilters,
    ServiceOut,
    ServiceSort,
    ServiceStatus,
    ServiceStatusPatch,
    ServiceUpdate,
    SessionType,
)
from app.services.service_service import ServiceService

router = APIRouter(prefix="/v1", tags=["Servicios"])

Svc = Annotated[ServiceService, Depends(get_service_service)]
User = Annotated[CurrentUser, Depends(get_current_user)]


def service_filters(
    search: Annotated[str | None, Query(max_length=100)] = None,
    skill_id: Annotated[str | None, Query(alias="skillId")] = None,
    area_id: Annotated[str | None, Query(alias="areaId")] = None,
    mentor_id: Annotated[str | None, Query(alias="mentorId")] = None,
    modality: Modality | None = None,
    type: SessionType | None = None,
    min_rating: Annotated[float | None, Query(alias="minRating", ge=0, le=5)] = None,
    price_max: Annotated[int | None, Query(alias="priceMax", ge=0)] = None,
    free: bool | None = None,
    day: Annotated[int | None, Query(ge=0, le=6)] = None,
    sort: ServiceSort = "relevance",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
) -> ServiceFilters:
    return ServiceFilters(
        search=search.strip() if search else None,
        skill_id=skill_id,
        area_id=area_id,
        mentor_id=mentor_id,
        modality=modality,
        type=type,
        min_rating=min_rating,
        price_max=price_max,
        free=free,
        day=day,
        sort=sort,
        page=page,
        page_size=page_size,
    )


def my_service_filters(
    status: ServiceStatus | None = None,
    area_id: Annotated[str | None, Query(alias="areaId")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    sort: ServiceSort = "createdAt:desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
) -> ServiceFilters:
    return ServiceFilters(
        status=status,
        area_id=area_id,
        search=search.strip() if search else None,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/services", response_model=Page[ServiceOut])
def search_services(
    _: User, svc: Svc, filters: Annotated[ServiceFilters, Depends(service_filters)]
):
    total, items = svc.search(filters)
    return Page[ServiceOut](
        total_records=total, page=filters.page, page_size=filters.page_size, items=items
    )


@router.get("/me/services", response_model=Page[ServiceOut])
def my_services(
    user: User, svc: Svc, filters: Annotated[ServiceFilters, Depends(my_service_filters)]
):
    total, items = svc.list_mine(user, filters)
    return Page[ServiceOut](
        total_records=total, page=filters.page, page_size=filters.page_size, items=items
    )


@router.get("/services/{service_id}", response_model=ServiceOut)
def get_service(service_id: str, _: User, svc: Svc):
    return svc.get(service_id)


@router.post("/services", response_model=ServiceOut, status_code=201)
def create_service(data: ServiceCreate, user: User, svc: Svc):
    return svc.create(user, data)


@router.put("/services/{service_id}", response_model=ServiceOut)
def update_service(service_id: str, data: ServiceUpdate, user: User, svc: Svc):
    return svc.update(user, service_id, data)


@router.patch("/services/{service_id}/status", response_model=ServiceOut)
def patch_service_status(service_id: str, body: ServiceStatusPatch, user: User, svc: Svc):
    return svc.set_status(user, service_id, body.status)


@router.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: str, user: User, svc: Svc) -> Response:
    svc.delete(user, service_id)
    return Response(status_code=204)
