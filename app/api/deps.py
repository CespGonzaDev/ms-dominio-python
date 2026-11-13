"""Inyección de dependencias. Los tests sobrescriben los getters de repositorio con fakes."""

from typing import Annotated

from fastapi import Depends

from app.repositories.catalog_repo import CosmosCatalogRepository
from app.repositories.cosmos_client import get_container
from app.repositories.protocols import CatalogRepository, ServiceRepository
from app.repositories.service_repo import CosmosServiceRepository
from app.services.catalog_service import CatalogService
from app.services.service_service import ServiceService


def get_catalog_repo() -> CatalogRepository:
    return CosmosCatalogRepository(get_container("catalog"))


def get_service_repo() -> ServiceRepository:
    return CosmosServiceRepository(get_container("services"))


def get_catalog_service(
    repo: Annotated[CatalogRepository, Depends(get_catalog_repo)],
) -> CatalogService:
    return CatalogService(repo)


def get_service_service(
    repo: Annotated[ServiceRepository, Depends(get_service_repo)],
) -> ServiceService:
    return ServiceService(repo)
