"""Databasequeries voor bronnen."""

from backend.app.database.client import get_supabase_client
from backend.app.schemas.source import Source


def list_sources(
    *,
    active_only: bool = True,
) -> list[Source]:
    """Haal de geconfigureerde bronnen uit Supabase."""

    client = get_supabase_client()

    query = (
        client
        .table("sources")
        .select("*")
        .order("name")
    )

    if active_only:
        query = query.eq("is_active", True)

    response = query.execute()

    return [
        Source.model_validate(source_data)
        for source_data in (response.data or [])
    ]

def get_source_by_code(code: str) -> Source:
    """Haal één databron op aan de hand van de unieke broncode."""

    client = get_supabase_client()

    response = (
        client
        .table("sources")
        .select("*")
        .eq("code", code)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise LookupError(
            f"Databron met code '{code}' is niet gevonden."
        )

    return Source.model_validate(response.data[0])