"""Inyección de dependencias. Los tests sobrescriben los getters de repositorio con fakes."""

from typing import Annotated

from fastapi import Depends

from app.clients.core_client import CoreGateway, HttpCoreClient
from app.core.config import get_settings
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


def get_core_client() -> CoreGateway:
    settings = get_settings()
    return HttpCoreClient(settings.core_api_url, settings.apim_subscription_key)


def get_catalog_service(
    repo: Annotated[CatalogRepository, Depends(get_catalog_repo)],
) -> CatalogService:
    return CatalogService(repo)


def get_service_service(
    repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    catalog_repo: Annotated[CatalogRepository, Depends(get_catalog_repo)],
    core_client: Annotated[CoreGateway, Depends(get_core_client)],
) -> ServiceService:
    return ServiceService(repo, catalog_repo, core_client)
