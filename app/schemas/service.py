"""Esquemas del servicio de mentoría alineados al contrato Fase I y ms-core (CatalogJson)."""

from dataclasses import dataclass
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from app.schemas.catalog import AreaOut, SkillOut
from app.schemas.common import CamelModel, UserSummary

ServiceStatus = Literal["activo", "inactivo"]
Modality = Literal["virtual", "presencial", "ambas"]
SessionType = Literal["individual", "grupal"]
Platform = Literal["google_meet", "zoom", "teams", "otra"]
Currency = Literal["CRC", "USD"]
DurationMinutes = Literal[30, 45, 60, 90, 120]
ServiceSort = Literal[
    "relevance",
    "rating:desc",
    "rating:asc",
    "price:asc",
    "price:desc",
    "createdAt:desc",
    "createdAt:asc",
    "updatedAt:desc",
    "updatedAt:asc",
]


class Price(CamelModel):
    amount: int = Field(ge=0)
    currency: Currency = "CRC"


class ServiceInput(CamelModel):
    """Campos editables para crear o actualizar un servicio de mentoría."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)
    area_id: str = Field(min_length=1)
    skill_ids: list[str] = Field(min_length=1)
    duration_minutes: DurationMinutes
    type: SessionType
    capacity: int = Field(default=1, ge=1, le=30)
    modality: Modality
    platforms: list[Platform] = Field(default_factory=list)
    price: Price | None = None
    available_days: list[int] = Field(default_factory=list)
    availability_summary: str | None = Field(default=None, max_length=200)

    @field_validator("price", mode="before")
    @classmethod
    def _normalize_price(cls, value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            if value < 0:
                raise ValueError("El precio no puede ser negativo")
            return None if value == 0 else {"amount": int(value), "currency": "CRC"}
        if isinstance(value, dict) and value.get("amount") == 0:
            return None
        return value

    @field_validator("available_days")
    @classmethod
    def _validate_days(cls, days: list[int]) -> list[int]:
        for day in days:
            if day < 0 or day > 6:
                raise ValueError("Los días disponibles deben estar entre 0 y 6")
        return sorted(set(days))

    @model_validator(mode="after")
    def _validate_domain_rules(self) -> "ServiceInput":
        if self.type == "individual":
            self.capacity = 1
        elif self.capacity < 2:
            raise ValueError("Las sesiones grupales requieren cupo mínimo de 2")

        if self.modality == "presencial":
            self.platforms = []
        elif not self.platforms:
            raise ValueError("Selecciona al menos una plataforma para modalidad virtual")
        return self


class ServiceCreate(ServiceInput):
    pass


class ServiceUpdate(ServiceInput):
    """PUT: reemplaza todos los campos editables."""


class ServiceStatusPatch(CamelModel):
    status: ServiceStatus


class ServiceOut(CamelModel):
    """Servicio público retornado por catálogo, detalle y listados."""

    id: str
    mentor_id: str
    mentor: UserSummary
    title: str
    description: str
    area: AreaOut
    skills: list[SkillOut]
    duration_minutes: int
    type: SessionType
    capacity: int
    modality: Modality
    platforms: list[Platform]
    price: Price | None = None
    availability_summary: str = "Por coordinar"
    available_days: list[int] = Field(default_factory=list)
    status: ServiceStatus = "activo"
    created_at_epoch_ms: int
    updated_at_epoch_ms: int


@dataclass(frozen=True)
class ServiceFilters:
    search: str | None = None
    skill_id: str | None = None
    area_id: str | None = None
    mentor_id: str | None = None
    modality: Modality | None = None
    type: SessionType | None = None
    min_rating: float | None = None
    price_max: int | None = None
    free: bool | None = None
    day: int | None = None
    status: ServiceStatus | None = None
    sort: ServiceSort = "relevance"
    page: int = 1
    page_size: int = 10

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
