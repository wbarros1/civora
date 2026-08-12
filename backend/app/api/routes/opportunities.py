"""API-routes voor publieke inhuuropdrachten."""

import logging

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status,
)

from backend.app.repositories.opportunities import (
    get_opportunity,
    list_opportunities,
)
from backend.app.schemas.opportunity_api import (
    OpportunityDetail,
    OpportunityListResponse,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()


@router.get(
    "",
    response_model=OpportunityListResponse,
    summary="Haal opdrachten op",
)
async def get_opportunities(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=120,
        description=(
            "Zoek op functietitel."
        ),
    ),
    client: str | None = Query(
        default=None,
        min_length=1,
        max_length=120,
        description=(
            "Filter op opdrachtgever."
        ),
    ),
    province: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "Filter op provincie."
        ),
    ),
    work_arrangement: str | None = Query(
        default=None,
        description=(
            "Filter op werkvorm."
        ),
    ),
    employment_relationship: str | None = Query(
        default=None,
        description=(
            "Filter op contractvorm."
        ),
    ),
    application_status: str | None = Query(
        default=None,
        description=(
            "Filter op reactiestatus."
        ),
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> OpportunityListResponse:
    """Geef actieve opdrachten terug."""

    try:
        items, has_more = (
            list_opportunities(
                search=search,
                client_name=client,
                province=province,
                work_arrangement=(
                    work_arrangement
                ),
                employment_relationship=(
                    employment_relationship
                ),
                application_status=(
                    application_status
                ),
                limit=limit,
                offset=offset,
            )
        )

        return OpportunityListResponse(
            items=items,
            limit=limit,
            offset=offset,
            has_more=has_more,
        )

    except Exception as exc:
        logger.exception(
            "De opdrachten konden niet "
            "uit Supabase worden opgehaald."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "De database is momenteel "
                "niet beschikbaar."
            ),
        ) from exc


@router.get(
    "/{opportunity_id}",
    response_model=OpportunityDetail,
    summary="Haal één opdracht op",
)
async def get_opportunity_detail(
    opportunity_id: str,
) -> OpportunityDetail:
    """Geef de volledige opdracht terug."""

    try:
        opportunity = (
            get_opportunity(
                opportunity_id
            )
        )

    except Exception as exc:
        logger.exception(
            "De opdracht kon niet uit "
            "Supabase worden opgehaald."
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "De database is momenteel "
                "niet beschikbaar."
            ),
        ) from exc

    if opportunity is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Opdracht niet gevonden."
            ),
        )

    return OpportunityDetail(
        **opportunity
    )