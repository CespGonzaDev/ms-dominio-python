"""Esquemas de descubrimiento: mentores, feed, recomendaciones e historial de búsqueda."""

from typing import Literal

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.common import CamelModel
from app.schemas.service import ServiceOut


class MentorCardOut(CamelModel):
    id: str
    full_name: str
    avatar_url: str | None = None
    rating_average: float = 0.0
    rating_count: int = 0
    headline: str = ""
    institution: str = ""
    skills: list[str] = Field(default_factory=list)
    completed_sessions: int = 0
    active_services: int = 0


class FeedServiceItem(CamelModel):
    kind: Literal["service"] = "service"
    data: ServiceOut


class FeedMentorItem(CamelModel):
    kind: Literal["mentor"] = "mentor"
    data: MentorCardOut


FeedItemOut = FeedServiceItem | FeedMentorItem


class RecommendationItemOut(CamelModel):
    service: ServiceOut
    reason: str


class RecommendationsResponse(CamelModel):
    items: list[RecommendationItemOut]


class SearchHistoryCreate(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    query: str = Field(min_length=1, max_length=120)
    skill_id: str | None = None
    area_id: str | None = None
