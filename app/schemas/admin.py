"""Esquemas de moderación y estadísticas para administración."""

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.catalog import AreaOut
from app.schemas.common import CamelModel
from app.schemas.report import ActionTaken, ReportStatus
from app.schemas.service import ServiceOut, ServiceStatus


class AdminServiceRowOut(ServiceOut):
    reports_count: int = 0


class AdminServiceStatusPatch(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    status: ServiceStatus
    reason: str = Field(min_length=5, max_length=300)


class AdminReportPatch(CamelModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    status: ReportStatus
    resolution: str | None = Field(default=None, max_length=500)
    action_taken: ActionTaken | None = None


class AdminServicesStats(CamelModel):
    total: int
    active: int


class AdminReviewsStats(CamelModel):
    total: int
    average: float


class AdminTopAreaStat(CamelModel):
    area: AreaOut
    services: int


class AdminStatsOut(CamelModel):
    services: AdminServicesStats
    reviews: AdminReviewsStats
    top_areas: list[AdminTopAreaStat]
