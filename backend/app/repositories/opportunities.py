"""Databasefuncties voor leesbare opportunities."""

from typing import Any

from backend.app.database.client import (
    get_supabase_client,
)


LIST_COLUMNS = (
    "id,"
    "source_reference,"
    "title,"
    "client_name,"
    "location,"
    "province,"
    "work_arrangement,"
    "start_date,"
    "end_date,"
    "application_deadline,"
    "hours_per_week_min,"
    "hours_per_week_max,"
    "rate_min,"
    "rate_max,"
    "rate_currency,"
    "rate_period,"
    "employment_relationship,"
    "source_status,"
    "application_status"
)


DETAIL_COLUMNS = (
    LIST_COLUMNS
    + ","
    "description,"
    "publication_date,"
    "duration_months,"
    "extension_possible,"
    "number_of_positions,"
    "education_level,"
    "minimum_years_experience,"
    "requirements,"
    "wishes,"
    "competencies,"
    "skills,"
    "contact_information,"
    "extraction_confidence"
)


def list_opportunities(
    *,
    search: str | None = None,
    client_name: str | None = None,
    province: str | None = None,
    work_arrangement: str | None = None,
    employment_relationship: str | None = None,
    application_status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], bool]:
    """Haal opdrachten voor de overzichtspagina op."""

    client = get_supabase_client()

    query = (
        client.table(
            "structured_opportunities"
        )
        .select(
            LIST_COLUMNS
        )
        .eq(
            "source_status",
            "active",
        )
    )

    if search:
        query = query.ilike(
            "title",
            f"%{search.strip()}%",
        )

    if client_name:
        query = query.ilike(
            "client_name",
            f"%{client_name.strip()}%",
        )

    if province:
        query = query.eq(
            "province",
            province,
        )

    if work_arrangement:
        query = query.eq(
            "work_arrangement",
            work_arrangement,
        )

    if employment_relationship:
        query = query.eq(
            "employment_relationship",
            employment_relationship,
        )

    if application_status:
        query = query.eq(
            "application_status",
            application_status,
        )

    response = (
        query
        .order(
            "application_deadline",
            desc=False,
        )
        .range(
            offset,
            offset + limit,
        )
        .execute()
    )

    rows = [
        row
        for row in (
            response.data or []
        )
        if isinstance(
            row,
            dict,
        )
    ]

    has_more = (
        len(rows) > limit
    )

    return (
        rows[:limit],
        has_more,
    )


def get_opportunity(
    opportunity_id: str,
) -> dict[str, Any] | None:
    """Haal één volledige opdracht op."""

    client = get_supabase_client()

    response = (
        client.table(
            "structured_opportunities"
        )
        .select(
            DETAIL_COLUMNS
        )
        .eq(
            "id",
            opportunity_id,
        )
        .limit(1)
        .execute()
    )

    rows = (
        response.data or []
    )

    if not rows:
        return None

    row = rows[0]

    if not isinstance(
        row,
        dict,
    ):
        return None

    return row