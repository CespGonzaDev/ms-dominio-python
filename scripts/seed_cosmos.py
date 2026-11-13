"""Crea la base y los contenedores de Cosmos DB: python -m scripts.seed_cosmos

Fase A: solo provisiona la estructura. La carga de datos iniciales se agrega en la Fase B.
Requiere COSMOS_ENDPOINT y COSMOS_KEY en el entorno (.env local).
"""

from app.repositories.cosmos_client import CONTAINERS, ensure_containers

if __name__ == "__main__":
    ensure_containers()
    print("Contenedores listos:", ", ".join(f"{n} ({pk})" for n, pk in CONTAINERS.items()))
