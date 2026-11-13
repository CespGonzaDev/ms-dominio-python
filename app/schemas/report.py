"""Esquemas de reportes de usuarios, servicios y reseñas."""

from typing import Literal

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.common import CamelModel, UserSummary

ReportTargetType = Literal["user", "service", "review"]
ReportReason = Literal["spam", "contenido_inapropiado", "fraude", "acoso", "otro"]
ReportStatus = Literal["pendiente", "en_revision", "resuelto", "descartado"]
ActionTaken = Literal[
    "ninguna",
    "desactivar_servicio",
    "ocultar_resena",
    "suspender_usuario",
]


class ReportCreate(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    target_type: ReportTargetType
    target_id: str = Field(min_length=1, max_length=120)
    reason: ReportReason
    description: str = Field(min_length=10, max_length=500)


class ReportOut(CamelModel):
    id: str
    reporter: UserSummary
    target_type: ReportTargetType
    target_id: str
    target_label: str
    reason: ReportReason
    description: str
    status: ReportStatus
    created_at_epoch_ms: int
    resolved_at_epoch_ms: int | None = None
    resolution: str | None = None
    action_taken: ActionTaken | None = None
