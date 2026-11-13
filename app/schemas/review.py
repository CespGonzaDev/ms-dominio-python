"""Esquemas de reseñas y resumen de calificaciones."""

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.common import CamelModel, UserSummary


class ReviewCreate(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=10, max_length=500)


class ReviewOut(CamelModel):
    id: str
    session_id: str
    mentor_id: str
    learner: UserSummary
    rating: int
    comment: str
    hidden: bool = False
    created_at_epoch_ms: int


class RatingSummaryOut(CamelModel):
    average: float = 0.0
    count: int = 0
    distribution: dict[str, int]
