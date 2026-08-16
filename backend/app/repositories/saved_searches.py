"""Databasefuncties voor opgeslagen zoekopdrachten."""

from typing import Any

from backend.app.database.client import (
    get_supabase_client,
)


def list_saved_searches(
    user_id: str,
) -> list[dict[str, Any]]:
    """Haal opgeslagen zoekopdrachten van één gebruiker op."""

    client = get_supabase_client()

    response = (
        client.table(
            "saved_searches"
        )
        .select(
            "id,"
            "user_id,"
            "name,"
            "filters,"
            "created_at,"
            "updated_at"
        )
        .eq(
            "user_id",
            user_id,
        )
        .order(
            "updated_at",
            desc=True,
        )
        .execute()
    )

    return [
        row
        for row in (
            response.data or []
        )
        if isinstance(
            row,
            dict,
        )
    ]


def create_saved_search(
    *,
    user_id: str,
    name: str,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """Bewaar één zoekopdracht."""

    client = get_supabase_client()

    response = (
        client.table(
            "saved_searches"
        )
        .insert(
            {
                "user_id": user_id,
                "name": name.strip(),
                "filters": filters,
            }
        )
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise RuntimeError(
            "De zoekopdracht kon "
            "niet worden opgeslagen."
        )

    row = rows[0]

    if not isinstance(
        row,
        dict,
    ):
        raise RuntimeError(
            "Supabase retourneerde een "
            "ongeldige zoekopdracht."
        )

    return row


def delete_saved_search(
    *,
    user_id: str,
    saved_search_id: str,
) -> bool:
    """Verwijder alleen een zoekopdracht van deze gebruiker."""

    client = get_supabase_client()

    existing_response = (
        client.table(
            "saved_searches"
        )
        .select("id")
        .eq(
            "id",
            saved_search_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    if not (
        existing_response.data
        or []
    ):
        return False

    (
        client.table(
            "saved_searches"
        )
        .delete()
        .eq(
            "id",
            saved_search_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    return True