import logging

from fastapi import Depends, FastAPI

from app.api.routes import health
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.security import verify_apim_cert


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title="SkillGrow - MS2 Dominio",
        description="Catálogo, servicios de mentoría, descubrimiento, reseñas y reportes.",
        version="1.0.0",
        # Todo el tráfico debe venir de APIM (certificado de cliente).
        dependencies=[Depends(verify_apim_cert)],
    )
    register_error_handlers(app)

    # /health en la raíz (ruta interna acordada). Los recursos de negocio irán bajo /v1.
    app.include_router(health.router)
    return app


app = create_app()
