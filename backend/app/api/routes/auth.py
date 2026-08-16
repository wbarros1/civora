"""API-routes voor authenticatie en gebruikersprofielen."""

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from backend.app.dependencies.auth import (
    get_current_identity,
)
from backend.app.repositories.profiles import (
    get_profile,
)
from backend.app.schemas.user import (
    AuthenticatedIdentity,
    CurrentUser,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()


@router.get(
    "/me",
    response_model=CurrentUser,
    summary="Haal ingelogde gebruiker op",
)
async def get_me(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(
            get_current_identity
        ),
    ],
) -> CurrentUser:
    """Geef identiteit en Civora-profiel terug."""

    try:
        profile = get_profile(
            identity.id
        )

    except Exception as exc:
        logger.exception(
            "Het gebruikersprofiel kon "
            "niet worden opgehaald."
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

    if profile is None:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Voor deze gebruiker bestaat "
                "geen Civora-profiel."
            ),
        )

    return CurrentUser(
        id=identity.id,
        email=identity.email,
        full_name=str(
            profile["full_name"]
        ),
        role=profile["role"],
        vakgroep=profile["vakgroep"],
    )