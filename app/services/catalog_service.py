from app.repositories.protocols import CatalogRepository


class CatalogService:
    def __init__(self, repo: CatalogRepository) -> None:
        self._repo = repo

    def list_areas(self) -> list[dict]:
        return self._repo.list_by_type("area")

    def list_skills(self, area_id: str | None = None, search: str | None = None) -> list[dict]:
        return self._repo.list_by_type("skill", area_id=area_id, search=search)
