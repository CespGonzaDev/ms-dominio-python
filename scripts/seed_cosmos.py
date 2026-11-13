"""Provisiona Cosmos DB y carga datos iniciales.

    python -m scripts.seed_cosmos --fixtures-dir data/seed/sample

Espera tres archivos JSON en el directorio indicado: areas.json, skills.json y services.json
(listas de objetos en camelCase). Es idempotente (upsert por id).

IMPORTANTE: data/seed/sample son datos de EJEMPLO para desarrollo. Los fixtures reales de la
Fase I (src/mocks/fixtures de la web) deben exportarse a ese mismo formato JSON y pasarse con
--fixtures-dir. Requiere COSMOS_ENDPOINT y COSMOS_KEY en el entorno (.env local).
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
    """Completa los valores por defecto y valida contra el esquema de salida."""
    now = now if now is not None else now_epoch_ms()
    doc = {
        "status": "active",
        "rating": 0,
        "reviewCount": 0,
        "createdAtEpochMs": now,
        "updatedAtEpochMs": now,
        **raw,
    }
    ServiceOut.model_validate(doc)  # falla aquí (seed) y no al leer en producción
    return doc


def _load(directory: Path, name: str) -> list[dict]:
    return json.loads((directory / name).read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixtures-dir", type=Path, default=Path("data/seed/sample"))
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
    print(f"Cargados: {len(areas)} áreas, {len(skills)} habilidades, {len(svc_docs)} servicios")


if __name__ == "__main__":
    main()
