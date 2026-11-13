from azure.cosmos.container import ContainerProxy

from app.repositories.cosmos_client import strip_system_fields


class CosmosCatalogRepository:
    """Contenedor `catalog` (pk /type): áreas y habilidades en particiones separadas."""

    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def list_by_type(self, item_type: str, area_id: str | None = None) -> list[dict]:
        query = "SELECT * FROM c WHERE c.type = @type"
        params = [{"name": "@type", "value": item_type}]
        if area_id:
            query += " AND c.areaId = @areaId"
            params.append({"name": "@areaId", "value": area_id})
        query += " ORDER BY c.name"
        items = self._container.query_items(
            query=query, parameters=params, partition_key=item_type
        )
        return [strip_system_fields(i) for i in items]
