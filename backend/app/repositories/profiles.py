"""Databasefuncties voor gebruikersprofielen."""

from typing import Any

from backend.app.database.client import (
    get_supabase_client,
)


def get_profile(
    user_id: str,
) -> dict[str, Any] | None:
    """Haal één Civora-profiel op."""

    client = get_supabase_client()

    response = (
        client.table(
            "profiles"
        )
        .select(
            "id,"
            "full_name,"
            "role,"
            "vakgroep"
        )
        .eq(
            "id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        return None

    row = rows[0]

    if not isinstance(
        row,
        dict,
    ):
        return None

    return row