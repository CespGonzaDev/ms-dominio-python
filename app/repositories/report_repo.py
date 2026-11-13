"""Contenedor `reports` (pk /status).

Nota de partición: al cambiar `status`, Cosmos no permite modificar la partition key con
replace_item; en ese caso se crea el documento en la nueva partición y luego se elimina
de la anterior.
"""

from azure.cosmos.container import ContainerProxy

from app.repositories.cosmos_client import strip_system_fields


class CosmosReportRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def list_filtered(
        self,
        *,
        status: str | None = None,
        target_type: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        clauses: list[str] = ["1 = 1"]
        params: list[dict] = []
        if status:
            clauses.append("c.status = @status")
            params.append({"name": "@status", "value": status})
        if target_type:
            clauses.append("c.targetType = @targetType")
            params.append({"name": "@targetType", "value": target_type})
        if search:
            clauses.append(
                "(CONTAINS(LOWER(c.targetLabel), @search)"
                " OR CONTAINS(LOWER(c.description), @search)"
                " OR CONTAINS(LOWER(c.reporter.fullName), @search))"
            )
            params.append({"name": "@search", "value": search.strip().lower()})

        query = (
            f"SELECT * FROM c WHERE {' AND '.join(clauses)} "
            "ORDER BY c.createdAtEpochMs DESC"
        )
        opts: dict = (
            {"partition_key": status} if status else {"enable_cross_partition_query": True}
        )
        items = self._container.query_items(query=query, parameters=params, **opts)
        return [strip_system_fields(i) for i in items]

    def get(self, report_id: str) -> dict | None:
        items = list(
            self._container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": report_id}],
                enable_cross_partition_query=True,
            )
        )
        return strip_system_fields(items[0]) if items else None

    def create(self, doc: dict) -> dict:
        return strip_system_fields(self._container.create_item(body=doc))

    def save_with_status(self, old_status: str, doc: dict) -> dict:
        if doc["status"] == old_status:
            return strip_system_fields(self._container.replace_item(item=doc["id"], body=doc))
        created = strip_system_fields(self._container.create_item(body=doc))
        self._container.delete_item(item=doc["id"], partition_key=old_status)
        return created
