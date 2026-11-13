"""Contenedor `reviews` (pk /mentorId)."""

from azure.cosmos.container import ContainerProxy

from app.repositories.cosmos_client import strip_system_fields


class CosmosReviewRepository:
    def __init__(self, container: ContainerProxy) -> None:
        self._container = container

    def list_by_mentor(
        self, mentor_id: str, *, rating: int | None = None, include_hidden: bool = False
    ) -> list[dict]:
        clauses = ["c.mentorId = @mentorId"]
        params: list[dict] = [{"name": "@mentorId", "value": mentor_id}]
        if not include_hidden:
            clauses.append("(NOT IS_DEFINED(c.hidden) OR c.hidden != true)")
        if rating is not None:
            clauses.append("c.rating = @rating")
            params.append({"name": "@rating", "value": rating})
        query = (
            f"SELECT * FROM c WHERE {' AND '.join(clauses)} "
            "ORDER BY c.createdAtEpochMs DESC"
        )
        items = self._container.query_items(
            query=query, parameters=params, partition_key=mentor_id
        )
        return [strip_system_fields(i) for i in items]

    def list_visible_ratings(self) -> list[int]:
        items = self._container.query_items(
            query=(
                "SELECT VALUE c.rating FROM c "
                "WHERE NOT IS_DEFINED(c.hidden) OR c.hidden != true"
            ),
            enable_cross_partition_query=True,
        )
        return [int(r) for r in items]

    def get(self, review_id: str) -> dict | None:
        items = list(
            self._container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": review_id}],
                enable_cross_partition_query=True,
            )
        )
        return strip_system_fields(items[0]) if items else None

    def exists_for_session_learner(self, session_id: str, learner_id: str) -> bool:
        items = list(
            self._container.query_items(
                query=(
                    "SELECT VALUE COUNT(1) FROM c "
                    "WHERE c.sessionId = @sessionId AND c.learnerId = @learnerId"
                ),
                parameters=[
                    {"name": "@sessionId", "value": session_id},
                    {"name": "@learnerId", "value": learner_id},
                ],
                enable_cross_partition_query=True,
            )
        )
        return (items[0] if items else 0) > 0

    def create(self, doc: dict) -> dict:
        return strip_system_fields(self._container.create_item(body=doc))

    def replace(self, doc: dict) -> dict:
        return strip_system_fields(self._container.replace_item(item=doc["id"], body=doc))
