"""API-routes voor publieke inhuuropdrachten."""

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from backend.app.dependencies.auth import (
    get_current_identity,
)
from backend.app.repositories.opportunities import (
    get_opportunity,
    list_opportunities,
)
from backend.app.repositories.profiles import (
    get_profile,
)
from backend.app.schemas.opportunity_api import (
    OpportunityDetail,
    OpportunityFeed,
    OpportunityListResponse,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
)
from backend.app.services.opportunity_classifier import (
    CLASSIFIER_VERSION,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()


VALID_VAKGROEPEN = {
    "procesmanagement",
    "data_ai",
    "ict",
    "finance",
}


@router.get(
    "",
    response_model=OpportunityListResponse,
    summary="Haal opdrachten op",
)
async def get_opportunities(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
    feed: OpportunityFeed = Query(
        default="for_you",
        description=(
            "Gebruik 'for_you' voor "
            "persoonlijke matches of 'all' "
            "voor alle actieve opdrachten."
        ),
    ),
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
        user_vakgroep: str | None = None

        if feed == "for_you":
            profile = get_profile(
                identity.id
            )

            if profile is None:
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Het gebruikersprofiel "
                        "ontbreekt."
                    ),
                )

            profile_vakgroep = (
                profile.get(
                    "vakgroep"
                )
            )

            if (
                not isinstance(
                    profile_vakgroep,
                    str,
                )
                or profile_vakgroep
                not in VALID_VAKGROEPEN
            ):
                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Het gebruikersprofiel "
                        "heeft geen geldige vakgroep."
                    ),
                )

            user_vakgroep = (
                profile_vakgroep
            )

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
                user_vakgroep=(
                    user_vakgroep
                ),
                classifier_version=(
                    CLASSIFIER_VERSION
                    if feed == "for_you"
                    else None
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
            feed=feed,
            vakgroep=user_vakgroep,
        )

    except HTTPException:
        raise

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
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
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