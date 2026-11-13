"""Contenedor `services` (pk /mentorId).

La búsqueda es cross-partition (el catálogo se explora por filtros, no por mentor); la gestión
del dueño (`/me/services`) va a una sola partición.
"""

from azure.cosmos.container import ContainerProxy

from app.repositories.cosmos_client import strip_system_fields
from app.schemas.service import ServiceFilters

_ORDER_BY = {
    "recent": "c.createdAtEpochMs DESC",
    "rating": "c.rating DESC",
    "priceAsc": "c.price ASC",
    "priceDesc": "c.price DESC",
}


def build_where(f: ServiceFilters) -> tuple[str, list[dict]]:
    """Arma el WHERE parametrizado. Nunca se concatenan valores del usuario en el SQL."""
    clauses = ["c.status = 'active'"]
    params: list[dict] = []

    def add(clause: str, name: str, value) -> None:
        clauses.append(clause)
        params.append({"name": name, "value": value})

    if f.search:
        add(
            "(CONTAINS(LOWER(c.title), @search) OR CONTAINS(LOWER(c.description), @search))",
            "@search",
            f.search.lower(),
        )
    if f.skill_id:
        add("ARRAY_CONTAINS(c.skillIds, @skillId)", "@skillId", f.skill_id)
    if f.area_id:
        add("c.areaId = @areaId", "@areaId", f.area_id)
    if f.modality:
        add("c.modality = @modality", "@modality", f.modality)
    if f.type:
        add("c.type = @type", "@type", f.type)
    if f.min_rating is not None:
        add("c.rating >= @minRating", "@minRating", f.min_rating)
    if f.price_max is not None:
        add("c.price <= @priceMax", "@priceMax", f.price_max)
    if f.free is True:
        clauses.append("c.price = 0")
    elif f.free is False:
        clauses.append("c.price > 0")
    if f.day:
        add("ARRAY_CONTAINS(c.availableDays, @day)", "@day", f.day)
    return " AND ".join(clauses), params


def build_search_query(f: ServiceFilters) -> tuple[str, str, list[dict]]:
    """Devuelve (consulta de página, consulta de conteo, parámetros)."""
    where, params = build_where(f)
    count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {where}"
    page_query = (
        f"SELECT * FROM c WHERE {where} ORDER BY {_ORDER_BY[f.sort]} "
        "OFFSET @offset LIMIT @limit"
    )
    return page_query, count_query, params


class CosmosServiceRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def search(self, filters: ServiceFilters) -> tuple[int, list[dict]]:
        page_query, count_query, params = build_search_query(filters)
        counts = list(
            self._container.query_items(
                query=count_query, parameters=params, enable_cross_partition_query=True
            )
        )
        total = counts[0] if counts else 0
        page_params = [
            *params,
            {"name": "@offset", "value": filters.offset},
            {"name": "@limit", "value": filters.page_size},
        ]
        items = self._container.query_items(
            query=page_query, parameters=page_params, enable_cross_partition_query=True
        )
        return total, [strip_system_fields(i) for i in items]

    def get(self, service_id: str) -> dict | None:
        # Se recibe solo el id (sin mentorId), por eso la consulta cruza particiones.
        items = list(
            self._container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": service_id}],
                enable_cross_partition_query=True,
            )
        )
        return strip_system_fields(items[0]) if items else None

    def list_by_mentor(self, mentor_id: str) -> list[dict]:
        items = self._container.query_items(
            query="SELECT * FROM c WHERE c.mentorId = @m ORDER BY c.createdAtEpochMs DESC",
            parameters=[{"name": "@m", "value": mentor_id}],
            partition_key=mentor_id,
        )
        return [strip_system_fields(i) for i in items]

    def create(self, doc: dict) -> dict:
        return strip_system_fields(self._container.create_item(body=doc))

    def replace(self, doc: dict) -> dict:
        return strip_system_fields(self._container.replace_item(item=doc["id"], body=doc))

    def delete(self, service_id: str, mentor_id: str) -> None:
        self._container.delete_item(item=service_id, partition_key=mentor_id)
