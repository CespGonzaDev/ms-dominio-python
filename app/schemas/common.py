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
