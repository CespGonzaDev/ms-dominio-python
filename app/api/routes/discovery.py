from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import get_discovery_service
from app.core.security import CurrentUser, get_current_user
from app.schemas.common import Page
from app.schemas.discovery import (
    FeedItemOut,
    MentorCardOut,
    RecommendationsResponse,
    SearchHistoryCreate,
)
from app.services.discovery_service import DiscoveryService

router = APIRouter(prefix="/v1", tags=["Descubrimiento"])

Svc = Annotated[DiscoveryService, Depends(get_discovery_service)]
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/mentors", response_model=Page[MentorCardOut])
def list_mentors(
    svc: Svc,
    search: Annotated[str | None, Query(max_length=100)] = None,
    area_id: Annotated[str | None, Query(alias="areaId")] = None,
    skill_id: Annotated[str | None, Query(alias="skillId")] = None,
    min_rating: Annotated[float | None, Query(alias="minRating", ge=0, le=5)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 12,
):
    total, items = svc.list_mentors(
        search=search,
        area_id=area_id,
        skill_id=skill_id,
        min_rating=min_rating,
        page=page,
        page_size=page_size,
    )
    return Page[MentorCardOut](total_records=total, page=page, page_size=page_size, items=items)


@router.get("/feed", response_model=Page[FeedItemOut])
def get_feed(
    user: User,
    svc: Svc,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 12,
):
    total, items = svc.feed(user, page=page, page_size=page_size)
    return Page[FeedItemOut](total_records=total, page=page, page_size=page_size, items=items)


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_recommendations(user: User, svc: Svc):
    return {"items": svc.recommendations(user)}


@router.get("/popular-searches", response_model=list[str])
def get_popular_searches(
    svc: Svc,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
):
    return svc.popular_searches(limit=limit)


@router.post("/me/search-history", status_code=204)
def save_search_history(body: SearchHistoryCreate, user: User, svc: Svc) -> Response:
    svc.record_search(user, body)
    return Response(status_code=204)
