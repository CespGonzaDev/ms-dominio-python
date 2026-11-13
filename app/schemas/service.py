"""Esquemas del servicio de mentoría.

SUPUESTO: la forma exacta de un servicio de la Fase I (src/types/api.ts de la web y
CONTRATO_API.md) no estaba disponible al construirlo. Los campos salen de lo que describe el
reparto (título, duración, tipo, cupo, modalidad, plataformas, precio, días, calificación).
Si el contrato real difiere, el único archivo a ajustar es éste (más los fixtures del seed).
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.common import CamelModel

ServiceStatus = Literal["active", "paused", "inactive"]
SortOption = Literal["recent", "rating", "priceAsc", "priceDesc"]


class MentorSummary(CamelModel):
    id: str
    name: str | None = None
    avatar: str | None = None


class ServiceBase(CamelModel):
    """Campos editables por el dueño del servicio."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    area_id: str = Field(min_length=1)
    skill_ids: list[str] = Field(default_factory=list)
    type: str = Field(min_length=1, max_length=50)
    modality: str = Field(min_length=1, max_length=50)
    platforms: list[str] = Field(default_factory=list)
    duration_minutes: int = Field(gt=0)
    capacity: int | None = Field(default=None, gt=0)
    price: float = Field(default=0, ge=0)
    available_days: list[str] = Field(default_factory=list)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(ServiceBase):
    """PUT: reemplaza todos los campos editables."""


class ServiceStatusPatch(CamelModel):
    status: ServiceStatus


class ServiceOut(ServiceBase):
    id: str
    mentor_id: str
    mentor: MentorSummary | None = None
    status: ServiceStatus = "active"
    rating: float = 0
    review_count: int = 0
    created_at_epoch_ms: int
    updated_at_epoch_ms: int


@dataclass(frozen=True)
class ServiceFilters:
    search: str | None = None
    skill_id: str | None = None
    area_id: str | None = None
    modality: str | None = None
    type: str | None = None
    min_rating: float | None = None
    price_max: float | None = None
    free: bool | None = None
    day: str | None = None
    sort: SortOption = "recent"
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
