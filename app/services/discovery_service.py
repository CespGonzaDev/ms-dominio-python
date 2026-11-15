"""Lógica de descubrimiento: mentores, feed mixto, recomendaciones e historial."""

import uuid

from app.clients.core_client import CoreGateway
from app.core.errors import now_epoch_ms
from app.core.security import CurrentUser
from app.repositories.protocols import SearchHistoryRepository, ServiceRepository
from app.schemas.discovery import SearchHistoryCreate


def _paginate(items: list, page: int, page_size: int) -> tuple[int, list]:
    offset = (page - 1) * page_size
    return len(items), items[offset : offset + page_size]


class DiscoveryService:
    def __init__(
        self,
        service_repo: ServiceRepository,
        history_repo: SearchHistoryRepository,
        core_client: CoreGateway | None = None,
    ) -> None:
        self._services = service_repo
        self._history = history_repo
        self._core = core_client

    def list_mentors(
        self,
        *,
        search: str | None = None,
        area_id: str | None = None,
        skill_id: str | None = None,
        min_rating: float | None = None,
        page: int = 1,
        page_size: int = 12,
    ) -> tuple[int, list[dict]]:
        entries = self._aggregate_mentors()
        needle = search.strip().lower() if search else None
        filtered: list[dict] = []
        for entry in entries:
            if area_id and area_id not in entry["area_ids"]:
                continue
            if skill_id and skill_id not in entry["skill_ids"]:
                continue
            card = entry["card"]
            if min_rating is not None and card["ratingAverage"] < min_rating:
                continue
            if needle:
                haystack = " ".join(
                    [card["fullName"], card["headline"], card["institution"], *card["skills"]]
                ).lower()
                if needle not in haystack:
                    continue
            filtered.append(card)
        return _paginate(filtered, page, page_size)

    def feed(self, user: CurrentUser, *, page: int = 1, page_size: int = 12) -> tuple[int, list]:
        active = [
            s for s in self._services.list_all(status="activo") if s.get("mentorId") != user.id
        ]
        active.sort(
            key=lambda s: (
                -(s.get("mentor") or {}).get("ratingAverage", 0.0),
                -s.get("updatedAtEpochMs", 0),
            )
        )
        mentors = [e["card"] for e in self._aggregate_mentors(active)]

        mixed: list[dict] = []
        si = 0
        mi = 0
        while si < len(active) or mi < len(mentors):
            for _ in range(2):
                if si < len(active):
                    mixed.append({"kind": "service", "data": active[si]})
                    si += 1
            if mi < len(mentors):
                mixed.append({"kind": "mentor", "data": mentors[mi]})
                mi += 1

        return _paginate(mixed, page, page_size)

    def recommendations(self, user: CurrentUser) -> list[dict]:
        history = self._history.list_by_user(user.id, limit=20)
        me = self._core.get_me(user.forward_headers()) if self._core else None
        interest_names = self._interest_map(me)

        hist_skills = {h["skillId"]: h.get("query") for h in history if h.get("skillId")}
        hist_areas = {h["areaId"]: h.get("query") for h in history if h.get("areaId")}
        hist_terms = [
            h["query"].strip().lower() for h in history if (h.get("query") or "").strip()
        ]

        candidates = [
            s for s in self._services.list_all(status="activo") if s.get("mentorId") != user.id
        ]
        scored: list[tuple[tuple[int, float, int], dict]] = []
        for svc in candidates:
            score, reason = self._score_service(
                svc, interest_names, hist_skills, hist_areas, hist_terms
            )
            mentor = svc.get("mentor") or {}
            key = (
                score,
                float(mentor.get("ratingAverage", 0.0)),
                int(svc.get("updatedAtEpochMs", 0)),
            )
            scored.append((key, {"service": svc, "reason": reason}))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:10]]

    def record_search(self, user: CurrentUser, data: SearchHistoryCreate) -> None:
        doc = {
            "id": str(uuid.uuid4()),
            "userId": user.id,
            "query": data.query,
            "atEpochMs": now_epoch_ms(),
        }
        if data.skill_id:
            doc["skillId"] = data.skill_id
        if data.area_id:
            doc["areaId"] = data.area_id
        self._history.create(doc)

    def _aggregate_mentors(self, services: list[dict] | None = None) -> list[dict]:
        source = services if services is not None else self._services.list_all(status="activo")
        grouped: dict[str, dict] = {}
        for svc in source:
            mid = svc["mentorId"]
            mentor = svc.get("mentor") or {}
            if mid not in grouped:
                grouped[mid] = {
                    "card": {
                        "id": mid,
                        "fullName": mentor.get("fullName") or mid,
                        "avatarUrl": mentor.get("avatarUrl"),
                        "ratingAverage": float(mentor.get("ratingAverage", 0.0)),
                        "ratingCount": int(mentor.get("ratingCount", 0)),
                        "headline": svc.get("mentorHeadline", ""),
                        "institution": svc.get("mentorInstitution", ""),
                        "skills": [],
                        "completedSessions": int(svc.get("mentorCompletedSessions", 0)),
                        "activeServices": 0,
                    },
                    "skill_ids": set(),
                    "area_ids": set(),
                }
            bucket = grouped[mid]
            card = bucket["card"]
            card["activeServices"] += 1
            if svc.get("areaId"):
                bucket["area_ids"].add(svc["areaId"])
            for sk in svc.get("skills", []):
                if sk.get("id"):
                    bucket["skill_ids"].add(sk["id"])
                name = sk.get("name")
                if name and name not in card["skills"]:
                    card["skills"].append(name)

        entries = list(grouped.values())
        entries.sort(
            key=lambda e: (
                -e["card"]["ratingAverage"],
                -e["card"]["ratingCount"],
                -e["card"]["completedSessions"],
                e["card"]["fullName"],
            )
        )
        return entries

    @staticmethod
    def _interest_map(me: dict | None) -> dict[str, str]:
        if not me:
            return {}
        interests = me.get("learningInterests") or []
        return {
            item["skillId"]: item.get("name", item["skillId"])
            for item in interests
            if item.get("skillId")
        }

    @staticmethod
    def _score_service(
        svc: dict,
        interest_names: dict[str, str],
        hist_skills: dict[str, str | None],
        hist_areas: dict[str, str | None],
        hist_terms: list[str],
    ) -> tuple[int, str]:
        skill_ids = svc.get("skillIds") or [s["id"] for s in svc.get("skills", [])]
        for sid in skill_ids:
            if sid in interest_names:
                return 3, f"Por tu interés en {interest_names[sid]}"
        for sid in skill_ids:
            if sid in hist_skills:
                term = hist_skills[sid] or svc.get("title", "")
                return 2, f"Basado en tu búsqueda de {term}"
        area_id = svc.get("areaId") or (svc.get("area") or {}).get("id")
        if area_id and area_id in hist_areas:
            area_name = (svc.get("area") or {}).get("name", "")
            return 2, f"Basado en tu interés en {area_name}"
        text = f"{svc.get('title', '')} {svc.get('description', '')}".lower()
        for term in hist_terms:
            if term in text:
                return 2, f"Basado en tu búsqueda de {term}"

        rating = float((svc.get("mentor") or {}).get("ratingAverage", 0.0))
        area_name = (svc.get("area") or {}).get("name", "")
        if rating >= 4.5 and area_name:
            return 1, f"Mejor calificado en {area_name}"
        return 0, "Recomendado para ti"

    def popular_searches(self, limit: int = 5) -> list[str]:
        """Devuelve los términos más buscados en `searchHistory`, completados con skills."""
        counts: dict[str, int] = {}
        labels: dict[str, str] = {}
        latest: dict[str, int] = {}

        for item in self._history.list_recent(200):
            raw_q = (item.get("query") or "").strip()
            if not raw_q:
                continue
            key = raw_q.casefold()
            counts[key] = counts.get(key, 0) + 1
            at = int(item.get("atEpochMs") or 0)
            if at >= latest.get(key, -1):
                latest[key] = at
                labels[key] = raw_q

        ranked = sorted(
            counts.keys(),
            key=lambda k: (-counts[k], -latest[k], labels[k]),
        )
        results = [labels[k] for k in ranked[:limit]]
        if len(results) >= limit:
            return results

        seen = {r.casefold() for r in results}
        skill_counts: dict[str, int] = {}
        skill_labels: dict[str, str] = {}
        for svc in self._services.list_all(status="activo"):
            for sk in svc.get("skills", []):
                name = (sk.get("name") or "").strip()
                if not name:
                    continue
                k = name.casefold()
                skill_counts[k] = skill_counts.get(k, 0) + 1
                skill_labels.setdefault(k, name)

        for k in sorted(skill_counts.keys(), key=lambda x: (-skill_counts[x], skill_labels[x])):
            if k not in seen:
                results.append(skill_labels[k])
                seen.add(k)
                if len(results) >= limit:
                    break
        return results
