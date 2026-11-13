"""Repositorios y clientes en memoria para probar rutas y servicios sin Cosmos ni red."""

from app.schemas.service import ServiceFilters


class FakeCatalogRepository:
    def __init__(self, docs: list[dict] | None = None) -> None:
        self.docs = docs or []

    def list_by_type(
        self,
        item_type: str,
        area_id: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        needle = search.strip().lower() if search else None
        return [
            d
            for d in self.docs
            if d["type"] == item_type
            and (area_id is None or d.get("areaId") == area_id)
            and (needle is None or needle in d.get("name", "").lower())
        ]


class FakeServiceRepository:
    """Registra filtros recibidos y emula las consultas básicas en memoria."""

    def __init__(self) -> None:
        self.docs: dict[str, dict] = {}
        self.last_filters: ServiceFilters | None = None

    def search(
        self, filters: ServiceFilters, *, active_only: bool = True
    ) -> tuple[int, list[dict]]:
        self.last_filters = filters
        items = [
            dict(d)
            for d in self.docs.values()
            if not d.get("deleted") and (not active_only or d.get("status") == "activo")
        ]
        if filters.mentor_id:
            items = [d for d in items if d["mentorId"] == filters.mentor_id]
        if filters.status:
            items = [d for d in items if d["status"] == filters.status]
        return len(items), items[filters.offset : filters.offset + filters.page_size]

    def list_all(self, *, status: str | None = None) -> list[dict]:
        return [
            dict(d)
            for d in self.docs.values()
            if not d.get("deleted") and (status is None or d.get("status") == status)
        ]

    def get(self, service_id: str) -> dict | None:
        doc = self.docs.get(service_id)
        return dict(doc) if doc else None

    def list_by_mentor(
        self, mentor_id: str, filters: ServiceFilters | None = None
    ) -> tuple[int, list[dict]]:
        f = filters or ServiceFilters(mentor_id=mentor_id, page_size=50)
        self.last_filters = f
        items = [dict(d) for d in self.docs.values() if d["mentorId"] == mentor_id]
        if f.status:
            items = [d for d in items if d["status"] == f.status]
        if f.area_id:
            items = [d for d in items if d.get("areaId") == f.area_id]
        if f.search:
            q = f.search.lower()
            items = [d for d in items if q in d.get("title", "").lower()]
        return len(items), items[f.offset : f.offset + f.page_size]

    def create(self, doc: dict) -> dict:
        self.docs[doc["id"]] = dict(doc)
        return dict(doc)

    def replace(self, doc: dict) -> dict:
        self.docs[doc["id"]] = dict(doc)
        return dict(doc)

    def delete(self, service_id: str, mentor_id: str) -> None:
        assert self.docs[service_id]["mentorId"] == mentor_id
        del self.docs[service_id]


class FakeCoreClient:
    """Doble de ms-core configurable en tests."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.users: dict[str, dict] = {}
        self.me_profile: dict | None = None
        self.suspended: list[tuple[str, str]] = []

    def get_session(self, session_id: str, headers: dict[str, str]) -> dict:
        if session_id not in self.sessions:
            from app.core.errors import AppError

            raise AppError(404, "SESSION_NOT_FOUND", f"La sesión '{session_id}' no existe")
        return dict(self.sessions[session_id])

    def get_user(self, user_id: str, headers: dict[str, str]) -> dict | None:
        u = self.users.get(user_id)
        return dict(u) if u else None

    def get_me(self, headers: dict[str, str]) -> dict | None:
        return dict(self.me_profile) if self.me_profile else None

    def suspend_user(self, user_id: str, reason: str, headers: dict[str, str]) -> bool:
        self.suspended.append((user_id, reason))
        return True
