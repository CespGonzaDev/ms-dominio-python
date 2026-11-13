"""Configuración del servicio, leída únicamente desde variables de entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "ms-dominio-python"
    log_level: str = "INFO"

    cosmos_endpoint: str = ""
    cosmos_key: str = ""
    cosmos_database: str = "skillgrow"

    # mTLS APIM -> backend. En producción debe ser true.
    apim_cert_check: bool = True
    apim_cert_thumbprint: str = ""

    core_api_url: str = ""
    apim_subscription_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
