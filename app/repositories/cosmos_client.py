"""Único punto de acceso a Azure Cosmos DB. El resto de capas no importan `azure.cosmos`."""

from functools import lru_cache

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.container import ContainerProxy
from azure.cosmos.database import DatabaseProxy

from app.core.config import get_settings

# Contenedor -> partition key (ver README, sección "Modelo de datos").
CONTAINERS: dict[str, str] = {
    "catalog": "/type",
    "services": "/mentorId",
    "reviews": "/mentorId",
    "reports": "/status",
    "searchHistory": "/userId",
}


@lru_cache
def get_database() -> DatabaseProxy:
    settings = get_settings()
    client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    return client.get_database_client(settings.cosmos_database)


def get_container(name: str) -> ContainerProxy:
    if name not in CONTAINERS:
        raise KeyError(f"Contenedor desconocido: {name}")
    return get_database().get_container_client(name)


def ensure_containers() -> None:
    """Crea la base y los contenedores si no existen (usado por scripts/seed_cosmos.py)."""
    settings = get_settings()
    client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    database = client.create_database_if_not_exists(settings.cosmos_database)
    for name, pk in CONTAINERS.items():
        database.create_container_if_not_exists(id=name, partition_key=PartitionKey(path=pk))
