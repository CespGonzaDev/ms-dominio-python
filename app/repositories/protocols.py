"""Contratos de los repositorios. Los servicios dependen de esto, no de Cosmos."""

from typing import Protocol

from app.schemas.service import ServiceFilters

Doc = dict


class CatalogRepository(Protocol):
    def list_by_type(self, item_type: str, area_id: str | None = None) -> list[Doc]: ...


class ServiceRepository(Protocol):
    def search(self, filters: ServiceFilters) -> tuple[int, list[Doc]]: ...

    def get(self, service_id: str) -> Doc | None: ...

    def list_by_mentor(self, mentor_id: str) -> list[Doc]: ...

    def create(self, doc: Doc) -> Doc: ...

    def replace(self, doc: Doc) -> Doc: ...

    def delete(self, service_id: str, mentor_id: str) -> None: ...
