"""Esquemas compartidos. Las propiedades JSON van en camelCase y las fechas en epoch ms."""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HealthResponse(CamelModel):
    status: str
    service: str
    timestamp_epoch_ms: int


class ErrorDetail(CamelModel):
    field: str
    issue: str


class ErrorResponse(CamelModel):
    code: str
    message: str
    details: list[ErrorDetail] = []
    timestamp_epoch_ms: int
    path: str


class UserSummary(CamelModel):
    """Resumen público de usuario compartido con Frontend y MS1."""

    id: str
    full_name: str
    avatar_url: str | None = None
    rating_average: float = 0.0
    rating_count: int = 0


class Page[T](CamelModel):
    """Envoltorio de listas paginadas: { totalRecords, page, pageSize, items }."""

    total_records: int
    page: int
    page_size: int
    items: list[T]
