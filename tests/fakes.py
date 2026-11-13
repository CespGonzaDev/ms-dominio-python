"""Repositorios en memoria para probar rutas y servicios sin Cosmos."""

from app.schemas.service import ServiceFilters


class FakeCatalogRepository:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []

    def list_by_type(self, item_type: str, area_id: str | None = None) -> list[dict]:
        return [
            d
            for d in self.docs
            if d["type"] == item_type and (area_id is None or d.get("areaId") == area_id)
        ]


class FakeServiceRepository:
    """No reimplementa los filtros de Cosmos (eso lo cubre test_service_query.py);
    registra los filtros recibidos y pagina sobre todos los documentos."""

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self.last_filters: ServiceFilters | None = None

    def search(self, filters: ServiceFilters) -> tuple[int, list[dict]]:
        self.last_filters = filters
        items = list(self.docs.values())
        return len(items), items[filters.offset : filters.offset + filters.page_size]

    def get(self, service_id: str) -> dict | None:
        doc = self.docs.get(service_id)
        return dict(doc) if doc else None

    def list_by_mentor(self, mentor_id: str) -> list[dict]:
        return [dict(d) for d in self.docs.values() if d["mentorId"] == mentor_id]

    def create(self, doc: dict) -> dict:
        self.docs[doc["id"]] = dict(doc)
        return dict(doc)

    def replace(self, doc: dict) -> dict:
        self.docs[doc["id"]] = dict(doc)
        return dict(doc)

    def delete(self, service_id: str, mentor_id: str) -> None:
        assert self.docs[service_id]["mentorId"] == mentor_id
        del self.docs[service_id]
