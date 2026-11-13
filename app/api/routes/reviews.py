from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_review_service
from app.core.security import CurrentUser, get_current_user
from app.schemas.common import Page
from app.schemas.review import RatingSummaryOut, ReviewCreate, ReviewOut
from app.services.review_service import ReviewService

router = APIRouter(prefix="/v1", tags=["Reseñas"])

Svc = Annotated[ReviewService, Depends(get_review_service)]
User = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("/sessions/{session_id}/review", response_model=ReviewOut, status_code=201)
def create_review(session_id: str, body: ReviewCreate, user: User, svc: Svc):
    return svc.create_for_session(user, session_id, body)


@router.get("/users/{user_id}/reviews", response_model=Page[ReviewOut])
def list_user_reviews(
    user_id: str,
    _: User,
    svc: Svc,
    rating: Annotated[int | None, Query(ge=1, le=5)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 10,
):
    total, items = svc.list_by_mentor(user_id, rating=rating, page=page, page_size=page_size)
    return Page[ReviewOut](total_records=total, page=page, page_size=page_size, items=items)


@router.get("/users/{user_id}/rating-summary", response_model=RatingSummaryOut)
def get_rating_summary(user_id: str, _: User, svc: Svc):
    return svc.rating_summary(user_id)
