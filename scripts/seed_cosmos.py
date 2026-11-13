"""Provisiona Cosmos DB y carga datos iniciales.

    python -m scripts.seed_cosmos --fixtures-dir data/seed/fase1

Espera archivos JSON en el directorio indicado: areas.json, skills.json y services.json
(obligatorios), más reviews.json, reports.json y search_history.json (opcionales).
Es idempotente (upsert por id). Requiere COSMOS_ENDPOINT y COSMOS_KEY en el entorno (.env local).
"""

import argparse
import json
from pathlib import Path

from app.core.errors import now_epoch_ms
from app.repositories.cosmos_client import CONTAINERS, ensure_containers, get_container
from app.schemas.service import ServiceOut


def normalize_catalog(items: list[dict], item_type: str) -> list[dict]:
    docs = []
    for raw in items:
        for key in ("id", "name"):
            if not raw.get(key):
                raise ValueError(f"Documento de catálogo sin '{key}': {raw}")
        docs.append({**raw, "type": item_type})
    return docs


def normalize_service(raw: dict, now: int | None = None) -> dict:
    """Completa los valores por defecto y valida contra el esquema real de salida."""
    now = now if now is not None else now_epoch_ms()
    mentor = dict(raw.get("mentor") or {"id": raw.get("mentorId", ""), "fullName": "Mentor"})
    mentor.setdefault("ratingAverage", 0.0)
    mentor.setdefault("ratingCount", 0)
    area_id = raw.get("areaId") or (raw.get("area") or {}).get("id")
    skill_ids = raw.get("skillIds") or [s["id"] for s in raw.get("skills", [])]
    doc = {
        "status": "activo",
        "deleted": False,
        "availabilitySummary": "Por coordinar",
        "availableDays": [],
        "createdAtEpochMs": now,
        "updatedAtEpochMs": now,
        **raw,
        "mentor": mentor,
        **({"areaId": area_id} if area_id else {}),
        **({"skillIds": skill_ids} if skill_ids else {}),
    }
    ServiceOut.model_validate(doc)
    return doc


def _load(directory: Path, name: str, required: bool = True) -> list[dict]:
    path = directory / name
    if not path.exists():
        if required:
            raise FileNotFoundError(f"No se encontró el fixture requerido: {path}")
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixtures-dir", type=Path, default=Path("data/seed/fase1"))
    args = parser.parse_args()

    ensure_containers()
    print("Contenedores listos:", ", ".join(f"{n} ({pk})" for n, pk in CONTAINERS.items()))

    catalog = get_container("catalog")
    services = get_container("services")
    areas = normalize_catalog(_load(args.fixtures_dir, "areas.json"), "area")
    skills = normalize_catalog(_load(args.fixtures_dir, "skills.json"), "skill")
    svc_docs = [normalize_service(s) for s in _load(args.fixtures_dir, "services.json")]

    for doc in [*areas, *skills]:
        catalog.upsert_item(doc)
    for doc in svc_docs:
        services.upsert_item(doc)

    extra_counts: dict[str, int] = {}
    for file_name, container_name in (
        ("reviews.json", "reviews"),
        ("reports.json", "reports"),
        ("search_history.json", "searchHistory"),
    ):
        docs = _load(args.fixtures_dir, file_name, required=False)
        if docs:
            cont = get_container(container_name)
            for doc in docs:
                cont.upsert_item(doc)
            extra_counts[container_name] = len(docs)

    summary = f"{len(areas)} áreas, {len(skills)} habilidades, {len(svc_docs)} servicios"
    if extra_counts:
        summary += ", " + ", ".join(f"{v} {k}" for k, v in extra_counts.items())
    print(f"Cargados: {summary}")


if __name__ == "__main__":
    main()
