"""Inyección de dependencias. Los tests sobrescriben los getters de repositorio con fakes."""

from typing import Annotated

from fastapi import Depends

from app.clients.core_client import CoreGateway, HttpCoreClient
from app.core.config import get_settings
from app.repositories.catalog_repo import CosmosCatalogRepository
from app.repositories.cosmos_client import get_container
from app.repositories.protocols import (
    CatalogRepository,
    ReportRepository,
    ReviewRepository,
    SearchHistoryRepository,
    ServiceRepository,
)
from app.repositories.report_repo import CosmosReportRepository
from app.repositories.review_repo import CosmosReviewRepository
from app.repositories.search_history_repo import CosmosSearchHistoryRepository
from app.repositories.service_repo import CosmosServiceRepository
from app.services.admin_service import AdminService
from app.services.catalog_service import CatalogService
from app.services.discovery_service import DiscoveryService
from app.services.report_service import ReportService
from app.services.review_service import ReviewService
from app.services.service_service import ServiceService


def get_catalog_repo() -> CatalogRepository:
    return CosmosCatalogRepository(get_container("catalog"))


def get_service_repo() -> ServiceRepository:
    return CosmosServiceRepository(get_container("services"))


def get_review_repo() -> ReviewRepository:
    return CosmosReviewRepository(get_container("reviews"))


def get_report_repo() -> ReportRepository:
    return CosmosReportRepository(get_container("reports"))


def get_search_history_repo() -> SearchHistoryRepository:
    return CosmosSearchHistoryRepository(get_container("searchHistory"))


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


def get_review_service(
    review_repo: Annotated[ReviewRepository, Depends(get_review_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    core_client: Annotated[CoreGateway, Depends(get_core_client)],
) -> ReviewService:
    return ReviewService(review_repo, service_repo, core_client)


def get_discovery_service(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    history_repo: Annotated[SearchHistoryRepository, Depends(get_search_history_repo)],
    core_client: Annotated[CoreGateway, Depends(get_core_client)],
) -> DiscoveryService:
    return DiscoveryService(service_repo, history_repo, core_client)


def get_report_service(
    report_repo: Annotated[ReportRepository, Depends(get_report_repo)],
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    review_repo: Annotated[ReviewRepository, Depends(get_review_repo)],
    core_client: Annotated[CoreGateway, Depends(get_core_client)],
) -> ReportService:
    return ReportService(report_repo, service_repo, review_repo, core_client)


def get_admin_service(
    service_repo: Annotated[ServiceRepository, Depends(get_service_repo)],
    report_repo: Annotated[ReportRepository, Depends(get_report_repo)],
    review_repo: Annotated[ReviewRepository, Depends(get_review_repo)],
    core_client: Annotated[CoreGateway, Depends(get_core_client)],
) -> AdminService:
    return AdminService(service_repo, report_repo, review_repo, core_client)
