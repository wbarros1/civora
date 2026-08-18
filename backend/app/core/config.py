"""Centrale applicatieconfiguratie."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Instellingen die vanuit omgevingsvariabelen worden geladen."""

    app_name: str = "Public Inhuur Platform API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = True

    api_v1_prefix: str = "/api/v1"

    supabase_url: str | None = None
    supabase_secret_key: SecretStr | None = None

    openai_api_key: SecretStr | None = None
    openai_extraction_model: str = (
        "gpt-5-mini"
    )
    openai_classification_model: str = (
        "gpt-5-mini"
    )
    openai_model: str = "gpt-5-mini"

    user_agent: str = "PublicInhuurPlatform/0.1"
    request_timeout_seconds: int = 30

    scraper_request_delay_seconds: float = 1.0
    scraper_max_items_per_run: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Geef één gedeelde configuratie-instantie terug."""

    return Settings()