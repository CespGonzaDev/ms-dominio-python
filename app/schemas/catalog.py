"""Catálogo de áreas y habilidades.

`extra="allow"`: los documentos de la Fase I pueden traer campos adicionales (íconos, colores...)
y deben llegar intactos al cliente.
"""

from pydantic import ConfigDict

from app.schemas.common import CamelModel


class AreaOut(CamelModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str


class SkillOut(CamelModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    area_id: str | None = None
