"""Supabase-databaseclient."""

from functools import lru_cache

from supabase import Client, create_client

from backend.app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Maak één gedeelde Supabase-client voor de backend."""

    settings = get_settings()

    if not settings.supabase_url:
        raise RuntimeError(
            "SUPABASE_URL ontbreekt in het .env-bestand."
        )

    if not settings.supabase_secret_key:
        raise RuntimeError(
            "SUPABASE_SECRET_KEY ontbreekt in het .env-bestand."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_secret_key.get_secret_value(),
    )