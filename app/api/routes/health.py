from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.errors import now_epoch_ms
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Salud"])


@router.get("/health", response_model=HealthResponse, response_model_by_alias=True)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="UP", service=settings.service_name, timestamp_epoch_ms=now_epoch_ms()
    )
