"""Lógica de negocio de reseñas y calificaciones."""

import uuid

from app.clients.core_client import CoreGateway
from app.core.errors import AppError, now_epoch_ms
from app.core.security import CurrentUser
from app.repositories.protocols import ReviewRepository, ServiceRepository
from app.schemas.review import ReviewCreate
from app.services.rating_helper import compute_rating_summary, recalculate_mentor_rating


class ReviewService:
    def __init__(
        self,
        review_repo: ReviewRepository,
        service_repo: ServiceRepository,
        core_client: CoreGateway,
    ) -> None:
        self._reviews = review_repo
        self._services = service_repo
        self._core = core_client

    def list_by_mentor(
        self, mentor_id: str, *, rating: int | None = None, page: int = 1, page_size: int = 10
    ) -> tuple[int, list[dict]]:
        items = self._reviews.list_by_mentor(mentor_id, rating=rating, include_hidden=False)
        offset = (page - 1) * page_size
        return len(items), items[offset : offset + page_size]

    def rating_summary(self, mentor_id: str) -> dict:
        reviews = self._reviews.list_by_mentor(mentor_id, include_hidden=False)
        return compute_rating_summary(reviews)

    def create_for_session(
        self, user: CurrentUser, session_id: str, data: ReviewCreate
    ) -> dict:
        session = self._core.get_session(session_id, user.forward_headers())
        learners = session.get("learners") or []
        learner_match = next((lr for lr in learners if lr.get("id") == user.id), None)
        if learner_match is None:
            raise AppError(
                403, "FORBIDDEN", "Solo los estudiantes participantes pueden reseñar la sesión"
            )
        if session.get("status") != "completada":
            raise AppError(
                400, "SESSION_NOT_COMPLETED", "Solo se pueden reseñar sesiones completadas"
            )
        if self._reviews.exists_for_session_learner(session_id, user.id):
            raise AppError(400, "ALREADY_REVIEWED", "Ya enviaste una reseña para esta sesión")

        mentor_obj = session.get("mentor") or {}
        mentor_id = mentor_obj.get("id") or session.get("mentorId")
        if not mentor_id:
            raise AppError(502, "UPSTREAM_ERROR", "La sesión consultada no indica mentor")

        doc = {
            "id": str(uuid.uuid4()),
            "sessionId": session_id,
            "mentorId": mentor_id,
            "learnerId": user.id,
            "learner": {
                "id": user.id,
                "fullName": learner_match.get("fullName") or user.name or user.id,
                "avatarUrl": learner_match.get("avatarUrl"),
                "ratingAverage": float(learner_match.get("ratingAverage", 0.0)),
                "ratingCount": int(learner_match.get("ratingCount", 0)),
            },
            "rating": data.rating,
            "comment": data.comment,
            "hidden": False,
            "createdAtEpochMs": now_epoch_ms(),
        }
        created = self._reviews.create(doc)
        recalculate_mentor_rating(mentor_id, self._reviews, self._services)
        return created
