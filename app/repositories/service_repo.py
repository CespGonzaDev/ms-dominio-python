"""Contenedor `services` (pk /mentorId).

La búsqueda es cross-partition (el catálogo se explora por filtros, no por mentor); la gestión
del dueño (`/me/services`) consulta una sola partición.
"""

from azure.cosmos.container import ContainerProxy

from app.repositories.cosmos_client import strip_system_fields
from app.schemas.service import ServiceFilters

_ORDER_BY = {
    "relevance": "c.mentor.ratingAverage DESC",
    "rating:desc": "c.mentor.ratingAverage DESC",
    "rating:asc": "c.mentor.ratingAverage ASC",
    "price:asc": "c.price.amount ASC",
    "price:desc": "c.price.amount DESC",
    "createdAt:desc": "c.createdAtEpochMs DESC",
    "createdAt:asc": "c.createdAtEpochMs ASC",
    "updatedAt:desc": "c.updatedAtEpochMs DESC",
    "updatedAt:asc": "c.updatedAtEpochMs ASC",
}


def build_where(f: ServiceFilters, *, active_only: bool = True) -> tuple[str, list[dict]]:
    """Arma el WHERE parametrizado. Nunca se concatenan valores del usuario en el SQL."""
    clauses: list[str] = ["(NOT IS_DEFINED(c.deleted) OR c.deleted != true)"]
    params: list[dict] = []

    def add(clause: str, name: str, value) -> None:
        clauses.append(clause)
        params.append({"name": name, "value": value})

    if active_only:
        clauses.append("c.status = 'activo'")
    elif f.status:
        add("c.status = @status", "@status", f.status)

    if f.mentor_id:
        add("c.mentorId = @mentorId", "@mentorId", f.mentor_id)
    if f.search:
        add(
            "(CONTAINS(LOWER(c.title), @search)"
            " OR CONTAINS(LOWER(c.description), @search)"
            " OR CONTAINS(LOWER(c.mentor.fullName), @search))",
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
        add("c.mentor.ratingAverage >= @minRating", "@minRating", f.min_rating)
    if f.price_max is not None:
        add(
            "(IS_NULL(c.price) OR NOT IS_DEFINED(c.price) OR c.price.amount <= @priceMax)",
            "@priceMax",
            f.price_max,
        )
    if f.free is True:
        clauses.append("(IS_NULL(c.price) OR NOT IS_DEFINED(c.price) OR c.price.amount = 0)")
    elif f.free is False:
        clauses.append("(IS_DEFINED(c.price) AND NOT IS_NULL(c.price) AND c.price.amount > 0)")
    if f.day is not None:
        add("ARRAY_CONTAINS(c.availableDays, @day)", "@day", f.day)

    return " AND ".join(clauses), params


def build_search_query(
    f: ServiceFilters, *, active_only: bool = True
) -> tuple[str, str, list[dict]]:
    """Devuelve (consulta de página, consulta de conteo, parámetros)."""
    where, params = build_where(f, active_only=active_only)
    order = _ORDER_BY[f.sort]
    count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {where}"
    page_query = f"SELECT * FROM c WHERE {where} ORDER BY {order} OFFSET @offset LIMIT @limit"
    return page_query, count_query, params


class CosmosServiceRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def _run_paged(
        self, filters: ServiceFilters, *, active_only: bool, partition_key: str | None = None
    ) -> tuple[int, list[dict]]:
        page_query, count_query, params = build_search_query(filters, active_only=active_only)
        query_opts: dict = (
            {"partition_key": partition_key}
            if partition_key
            else {"enable_cross_partition_query": True}
        )
        counts = list(
            self._container.query_items(query=count_query, parameters=params, **query_opts)
        )
        total = counts[0] if counts else 0
        page_params = [
            *params,
            {"name": "@offset", "value": filters.offset},
            {"name": "@limit", "value": filters.page_size},
        ]
        items = self._container.query_items(query=page_query, parameters=page_params, **query_opts)
        return total, [strip_system_fields(i) for i in items]

    def search(
        self, filters: ServiceFilters, *, active_only: bool = True
    ) -> tuple[int, list[dict]]:
        return self._run_paged(filters, active_only=active_only)

    def list_all(self, *, status: str | None = None) -> list[dict]:
        query = "SELECT * FROM c WHERE (NOT IS_DEFINED(c.deleted) OR c.deleted != true)"
        params: list[dict] = []
        if status:
            query += " AND c.status = @status"
            params.append({"name": "@status", "value": status})
        items = self._container.query_items(
            query=query, parameters=params, enable_cross_partition_query=True
        )
        return [strip_system_fields(i) for i in items]

    def get(self, service_id: str) -> dict | None:
        items = list(
            self._container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": service_id}],
                enable_cross_partition_query=True,
            )
        )
        return strip_system_fields(items[0]) if items else None

    def list_by_mentor(
        self, mentor_id: str, filters: ServiceFilters | None = None
    ) -> tuple[int, list[dict]]:
        f = filters or ServiceFilters(mentor_id=mentor_id, sort="createdAt:desc", page_size=50)
        return self._run_paged(f, active_only=False, partition_key=mentor_id)

    def create(self, doc: dict) -> dict:
        return strip_system_fields(self._container.create_item(body=doc))

    def replace(self, doc: dict) -> dict:
        return strip_system_fields(self._container.replace_item(item=doc["id"], body=doc))

    def delete(self, service_id: str, mentor_id: str) -> None:
        self._container.delete_item(item=service_id, partition_key=mentor_id)
