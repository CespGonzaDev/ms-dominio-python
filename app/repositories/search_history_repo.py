"""Contenedor `searchHistory` (pk /userId)."""

from azure.cosmos.container import ContainerProxy

from app.repositories.cosmos_client import strip_system_fields


class CosmosSearchHistoryRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def list_by_user(self, user_id: str, limit: int = 20) -> list[dict]:
        query = (
            "SELECT * FROM c WHERE c.userId = @userId "
            "ORDER BY c.atEpochMs DESC OFFSET 0 LIMIT @limit"
        )
        items = self._container.query_items(
            query=query,
            parameters=[
                {"name": "@userId", "value": user_id},
                {"name": "@limit", "value": limit},
            ],
            partition_key=user_id,
        )
        return [strip_system_fields(i) for i in items]

    def create(self, doc: dict) -> dict:
        return strip_system_fields(self._container.create_item(body=doc))
