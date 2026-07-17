"""API-routes voor databronnen."""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.repositories.sources import list_sources
from backend.app.schemas.source import Source

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=list[Source],
    summary="Haal databronnen op",
)
async def get_sources(
    active_only: bool = Query(
        default=True,
        description="Toon alleen actieve bronnen.",
    ),
) -> list[Source]:
    """Geef de geconfigureerde bronnen terug."""

    try:
        return list_sources(active_only=active_only)

    except Exception as exc:
        logger.exception(
            "De databronnen konden niet uit Supabase worden opgehaald."
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="De database is momenteel niet beschikbaar.",
        ) from exc