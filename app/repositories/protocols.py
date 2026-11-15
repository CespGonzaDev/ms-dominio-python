"""Contratos de los repositorios. Los servicios dependen de esto, no de Cosmos."""

from typing import Protocol

from app.schemas.service import ServiceFilters

Doc = dict


class CatalogRepository(Protocol):
    def list_by_type(
        self,
        item_type: str,
        area_id: str | None = None,
        search: str | None = None,
    ) -> list[Doc]: ...


class ServiceRepository(Protocol):
    def search(
        self, filters: ServiceFilters, *, active_only: bool = True
    ) -> tuple[int, list[Doc]]: ...

    def list_all(self, *, status: str | None = None) -> list[Doc]: ...

    def get(self, service_id: str) -> Doc | None: ...

    def list_by_mentor(
        self, mentor_id: str, filters: ServiceFilters | None = None
    ) -> tuple[int, list[Doc]]: ...

    def create(self, doc: Doc) -> Doc: ...

    def replace(self, doc: Doc) -> Doc: ...

    def delete(self, service_id: str, mentor_id: str) -> None: ...


class ReviewRepository(Protocol):
    def list_by_mentor(
        self, mentor_id: str, *, rating: int | None = None, include_hidden: bool = False
    ) -> list[Doc]: ...

    def list_visible_ratings(self) -> list[int]: ...

    def get(self, review_id: str) -> Doc | None: ...

    def exists_for_session_learner(self, session_id: str, learner_id: str) -> bool: ...

    def create(self, doc: Doc) -> Doc: ...

    def replace(self, doc: Doc) -> Doc: ...


class ReportRepository(Protocol):
    def list_filtered(
        self,
        *,
        status: str | None = None,
        target_type: str | None = None,
        search: str | None = None,
    ) -> list[Doc]: ...

    def get(self, report_id: str) -> Doc | None: ...

    def create(self, doc: Doc) -> Doc: ...

    def save_with_status(self, old_status: str, doc: Doc) -> Doc: ...


class SearchHistoryRepository(Protocol):
    def list_by_user(self, user_id: str, limit: int = 20) -> list[Doc]: ...

    def list_recent(self, limit: int = 200) -> list[Doc]: ...

    def create(self, doc: Doc) -> Doc: ...
